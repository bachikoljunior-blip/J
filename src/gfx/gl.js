// ============================================================================
//  gl.js — thin WebGL wrapper.
//  Targets GLSL ES 1.00 so a single shader source works on both WebGL1 and
//  WebGL2; instancing/depth-texture/uint-index differences are papered over
//  here so nothing above this file has to branch on context version.
// ============================================================================

export class GL {
  constructor(canvas, opts = {}) {
    const attrs = {
      alpha: false,
      antialias: false,          // we resolve aliasing in the post pass instead
      depth: true,
      stencil: false,
      powerPreference: 'high-performance',
      preserveDrawingBuffer: false,
      failIfMajorPerformanceCaveat: false,
      ...opts,
    };

    let gl = canvas.getContext('webgl2', attrs);
    this.isWebGL2 = !!gl;
    if (!gl) {
      gl = canvas.getContext('webgl', attrs) || canvas.getContext('experimental-webgl', attrs);
    }
    if (!gl) throw new Error('WebGL is not available on this device.');

    this.gl = gl;
    this.canvas = canvas;

    // --- capability probing -------------------------------------------------
    if (this.isWebGL2) {
      this.instancedArrays = true;
      this.uintIndices = true;
      this.derivatives = true;
      this.depthTexture = true;
      this.drawInstanced = (mode, count, type, offset, primCount) =>
        gl.drawElementsInstanced(mode, count, type, offset, primCount);
      this.drawArraysInstancedFn = (mode, first, count, primCount) =>
        gl.drawArraysInstanced(mode, first, count, primCount);
      this.vertexAttribDivisorFn = (i, d) => gl.vertexAttribDivisor(i, d);
      this.createVAO = () => gl.createVertexArray();
      this.bindVAO = (v) => gl.bindVertexArray(v);
    } else {
      const inst = gl.getExtension('ANGLE_instanced_arrays');
      this.instancedArrays = !!inst;
      this.uintIndices = !!gl.getExtension('OES_element_index_uint');
      this.derivatives = !!gl.getExtension('OES_standard_derivatives');
      this.depthTexture = !!gl.getExtension('WEBGL_depth_texture');
      const vaoExt = gl.getExtension('OES_vertex_array_object');
      this.drawInstanced = inst
        ? (mode, count, type, offset, primCount) => inst.drawElementsInstancedANGLE(mode, count, type, offset, primCount)
        : null;
      this.drawArraysInstancedFn = inst
        ? (mode, first, count, primCount) => inst.drawArraysInstancedANGLE(mode, first, count, primCount)
        : null;
      this.vertexAttribDivisorFn = inst ? (i, d) => inst.vertexAttribDivisorANGLE(i, d) : () => {};
      this.createVAO = vaoExt ? () => vaoExt.createVertexArrayOES() : () => null;
      this.bindVAO = vaoExt ? (v) => vaoExt.bindVertexArrayOES(v) : () => {};
    }

    this.maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
    const dbgInfo = gl.getExtension('WEBGL_debug_renderer_info');
    this.rendererName = dbgInfo ? gl.getParameter(dbgInfo.UNMASKED_RENDERER_WEBGL) : 'unknown';

    // Anisotropic filtering is a cheap win for the terrain texture at glancing
    // angles; absent on some mobile drivers, so it stays optional.
    this.aniso = gl.getExtension('EXT_texture_filter_anisotropic')
      || gl.getExtension('WEBKIT_EXT_texture_filter_anisotropic');
    this.maxAniso = this.aniso ? gl.getParameter(this.aniso.MAX_TEXTURE_MAX_ANISOTROPY_EXT) : 1;

    this._program = null;
    this.drawCalls = 0;
    this.triangles = 0;
    this.tag = 'other';
    this.byTag = Object.create(null);
    this.triByTag = Object.create(null);
  }

  resetStats() {
    this.drawCalls = 0;
    this.triangles = 0;
    for (const k in this.byTag) this.byTag[k] = 0;
    for (const k in this.triByTag) this.triByTag[k] = 0;
  }

  /** Label subsequent draws so the frame cost can be attributed. */
  setTag(tag) { this.tag = tag; }
  countDraw(n = 1) {
    this.drawCalls += n;
    this.byTag[this.tag] = (this.byTag[this.tag] || 0) + n;
  }

  countTris(n) {
    this.triangles += n;
    this.triByTag[this.tag] = (this.triByTag[this.tag] || 0) + n;
  }

  // -------------------------------------------------------------------------
  //  Shaders
  // -------------------------------------------------------------------------

  compile(type, source, label) {
    const gl = this.gl;
    const sh = gl.createShader(type);
    gl.shaderSource(sh, source);
    gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
      const log = gl.getShaderInfoLog(sh);
      const numbered = source.split('\n').map((l, i) => `${String(i + 1).padStart(3)}| ${l}`).join('\n');
      gl.deleteShader(sh);
      throw new Error(`Shader compile failed [${label}]:\n${log}\n${numbered}`);
    }
    return sh;
  }

  program(vsSource, fsSource, label = 'program') {
    const gl = this.gl;
    // Prelude injects the extension pragma before anything else, which GLSL requires.
    const prefix = this.derivatives && !this.isWebGL2
      ? '#extension GL_OES_standard_derivatives : enable\n'
      : '';
    const vs = this.compile(gl.VERTEX_SHADER, vsSource, label + '.vert');
    const fs = this.compile(gl.FRAGMENT_SHADER, prefix + fsSource, label + '.frag');
    const p = gl.createProgram();
    gl.attachShader(p, vs);
    gl.attachShader(p, fs);
    gl.linkProgram(p);
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
      const log = gl.getProgramInfoLog(p);
      gl.deleteProgram(p);
      throw new Error(`Program link failed [${label}]: ${log}`);
    }

    // Cache locations up front — getUniformLocation is slow enough to matter
    // if called per-frame on low-end phones.
    const uniforms = Object.create(null);
    const nU = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS);
    for (let i = 0; i < nU; i++) {
      const info = gl.getActiveUniform(p, i);
      const name = info.name.replace(/\[0\]$/, '');
      uniforms[name] = gl.getUniformLocation(p, name);
    }
    const attribs = Object.create(null);
    const nA = gl.getProgramParameter(p, gl.ACTIVE_ATTRIBUTES);
    for (let i = 0; i < nA; i++) {
      const info = gl.getActiveAttrib(p, i);
      attribs[info.name] = gl.getAttribLocation(p, info.name);
    }
    return { handle: p, uniforms, attribs, label };
  }

  use(prog) {
    if (this._program === prog) return prog;
    this._program = prog;
    this.gl.useProgram(prog.handle);
    return prog;
  }

  // Uniform setters that silently no-op when the uniform was optimised out.
  u1f(p, n, v) { const l = p.uniforms[n]; if (l) this.gl.uniform1f(l, v); }
  u1i(p, n, v) { const l = p.uniforms[n]; if (l) this.gl.uniform1i(l, v); }
  u2f(p, n, a, b) { const l = p.uniforms[n]; if (l) this.gl.uniform2f(l, a, b); }
  u3f(p, n, a, b, c) { const l = p.uniforms[n]; if (l) this.gl.uniform3f(l, a, b, c); }
  u4f(p, n, a, b, c, d) { const l = p.uniforms[n]; if (l) this.gl.uniform4f(l, a, b, c, d); }
  u3v(p, n, v) { const l = p.uniforms[n]; if (l) this.gl.uniform3f(l, v.x, v.y, v.z); }
  umat(p, n, m) { const l = p.uniforms[n]; if (l) this.gl.uniformMatrix4fv(l, false, m); }

  // -------------------------------------------------------------------------
  //  Buffers
  // -------------------------------------------------------------------------

  buffer(target, data, usage) {
    const gl = this.gl;
    const b = gl.createBuffer();
    gl.bindBuffer(target, b);
    gl.bufferData(target, data, usage || gl.STATIC_DRAW);
    return b;
  }

  vbo(data, usage) { return this.buffer(this.gl.ARRAY_BUFFER, data, usage); }
  ibo(data, usage) { return this.buffer(this.gl.ELEMENT_ARRAY_BUFFER, data, usage); }

  updateBuffer(target, buf, data, count) {
    const gl = this.gl;
    gl.bindBuffer(target, buf);
    if (count !== undefined && data.length !== count) {
      gl.bufferSubData(target, 0, data.subarray(0, count));
    } else {
      gl.bufferSubData(target, 0, data);
    }
  }

  // -------------------------------------------------------------------------
  //  Textures & framebuffers
  // -------------------------------------------------------------------------

  texture2D({ width, height, data = null, format, type, filter, wrap, mip = false }) {
    const gl = this.gl;
    format = format || gl.RGBA;
    type = type || gl.UNSIGNED_BYTE;
    filter = filter || gl.LINEAR;
    wrap = wrap || gl.CLAMP_TO_EDGE;
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texImage2D(gl.TEXTURE_2D, 0, format, width, height, 0, format, type, data);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, mip ? gl.LINEAR_MIPMAP_LINEAR : filter);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, wrap);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, wrap);
    if (mip) gl.generateMipmap(gl.TEXTURE_2D);
    if (mip && this.aniso) {
      gl.texParameterf(gl.TEXTURE_2D, this.aniso.TEXTURE_MAX_ANISOTROPY_EXT, Math.min(4, this.maxAniso));
    }
    return t;
  }

  textureFromCanvas(cvs, { mip = true, wrap } = {}) {
    const gl = this.gl;
    wrap = wrap || gl.REPEAT;
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, cvs);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, mip ? gl.LINEAR_MIPMAP_LINEAR : gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, wrap);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, wrap);
    if (mip) gl.generateMipmap(gl.TEXTURE_2D);
    if (mip && this.aniso) {
      gl.texParameterf(gl.TEXTURE_2D, this.aniso.TEXTURE_MAX_ANISOTROPY_EXT, Math.min(4, this.maxAniso));
    }
    return t;
  }

  /** Colour target with optional depth. Used for the main scene pass. */
  createRenderTarget(width, height, { depth = true, filter } = {}) {
    const gl = this.gl;
    filter = filter || gl.LINEAR;
    const color = this.texture2D({ width, height, filter });
    const fbo = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, color, 0);
    let depthBuf = null;
    if (depth) {
      depthBuf = gl.createRenderbuffer();
      gl.bindRenderbuffer(gl.RENDERBUFFER, depthBuf);
      gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, width, height);
      gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, depthBuf);
    }
    const ok = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    return { fbo, color, depthBuf, width, height, ok };
  }

  /**
   * Shadow map. WEBGL_depth_texture is not universal on mobile, so when it is
   * missing we fall back to encoding depth into an RGBA colour target.
   */
  createShadowTarget(size) {
    const gl = this.gl;
    const useDepthTex = this.depthTexture;
    const fbo = gl.createFramebuffer();
    gl.bindFramebuffer(gl.FRAMEBUFFER, fbo);

    let color = null, depthTex = null, depthBuf = null;
    if (useDepthTex) {
      depthTex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, depthTex);
      const internal = this.isWebGL2 ? gl.DEPTH_COMPONENT24 : gl.DEPTH_COMPONENT;
      const type = this.isWebGL2 ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT;
      if (this.isWebGL2) {
        gl.texStorage2D(gl.TEXTURE_2D, 1, internal, size, size);
      } else {
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.DEPTH_COMPONENT, size, size, 0, gl.DEPTH_COMPONENT, type, null);
      }
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.TEXTURE_2D, depthTex, 0);
      // WebGL1 requires a colour attachment for completeness on many drivers.
      if (!this.isWebGL2) {
        color = this.texture2D({ width: size, height: size, filter: gl.NEAREST });
        gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, color, 0);
      } else {
        gl.drawBuffers([gl.NONE]);
        gl.readBuffer(gl.NONE);
      }
    } else {
      color = this.texture2D({ width: size, height: size, filter: gl.NEAREST });
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, color, 0);
      depthBuf = gl.createRenderbuffer();
      gl.bindRenderbuffer(gl.RENDERBUFFER, depthBuf);
      gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, size, size);
      gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, depthBuf);
    }

    const status = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    if (this.isWebGL2) { gl.drawBuffers([gl.BACK]); }

    if (status !== gl.FRAMEBUFFER_COMPLETE && useDepthTex) {
      // Depth-texture path unsupported in practice — retry as packed RGBA.
      this.depthTexture = false;
      return this.createShadowTarget(size);
    }
    return {
      fbo, size,
      texture: useDepthTex ? depthTex : color,
      packed: !useDepthTex,
      ok: status === gl.FRAMEBUFFER_COMPLETE,
    };
  }

  bindTexture(unit, tex) {
    const gl = this.gl;
    gl.activeTexture(gl.TEXTURE0 + unit);
    gl.bindTexture(gl.TEXTURE_2D, tex);
  }

  bindTarget(rt) {
    const gl = this.gl;
    if (!rt) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    } else {
      gl.bindFramebuffer(gl.FRAMEBUFFER, rt.fbo);
      gl.viewport(0, 0, rt.width || rt.size, rt.height || rt.size);
    }
  }
}
