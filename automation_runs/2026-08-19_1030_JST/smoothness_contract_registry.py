from __future__ import annotations
from dataclasses import dataclass,asdict
import hashlib,json,math


def _canon(obj)->bytes:
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()

@dataclass(frozen=True)
class ContractManifest:
    contract_id: str
    schema_version: int
    family: str
    assumptions: tuple[str,...]
    proof_reference: str
    implementation_sha256: str
    calibrator_kind: str
    failure_semantics: str

    def digest(self)->str:
        return hashlib.sha256(_canon(asdict(self))).hexdigest()

@dataclass(frozen=True)
class SmoothnessEvidenceRecord:
    contract_id: str
    manifest_digest: str
    input_digest: str
    status: str
    lipschitz_upper: float
    failure_probability: float
    calibrator_kind: str

@dataclass(frozen=True)
class RegistryDecision:
    status: str
    lipschitz_upper: float
    failure_probability: float
    reason: str

class ContractRegistry:
    def __init__(self): self._manifests={}
    def register(self,manifest:ContractManifest):
        if not manifest.contract_id or manifest.schema_version<1:raise ValueError('bad manifest identity')
        if len(manifest.implementation_sha256)!=64 or any(c not in '0123456789abcdef' for c in manifest.implementation_sha256):raise ValueError('bad implementation digest')
        old=self._manifests.get(manifest.contract_id)
        if old is not None and old.digest()!=manifest.digest():raise ValueError('contract id collision/version mutation')
        self._manifests[manifest.contract_id]=manifest
        return manifest.digest()
    def verify(self,record:SmoothnessEvidenceRecord)->RegistryDecision:
        m=self._manifests.get(record.contract_id)
        if m is None:return RegistryDecision('abstain_unknown_contract',math.inf,1.0,'contract is not registered')
        if record.manifest_digest!=m.digest():return RegistryDecision('abstain_manifest_tamper',math.inf,1.0,'manifest digest mismatch')
        if record.calibrator_kind!=m.calibrator_kind:return RegistryDecision('abstain_wrong_calibrator',math.inf,1.0,'record calibrator is not authorized by manifest')
        if record.status not in ('certified_external','certified_conditional_on_family','certified_conditional_on_catalog'):
            return RegistryDecision('abstain_uncertified_status',math.inf,1.0,'upstream evidence did not certify a bound')
        if not record.input_digest or len(record.input_digest)!=64:return RegistryDecision('abstain_missing_input_provenance',math.inf,1.0,'input digest missing')
        if not math.isfinite(record.lipschitz_upper) or record.lipschitz_upper<0:return RegistryDecision('abstain_invalid_bound',math.inf,1.0,'nonfinite/negative bound')
        if not 0<=record.failure_probability<1:return RegistryDecision('abstain_invalid_failure_probability',math.inf,1.0,'invalid failure probability')
        return RegistryDecision('accepted_registered_certificate',float(record.lipschitz_upper),float(record.failure_probability),'manifest, authorized calibrator kind, input digest and numeric certificate fields verified')


def sha256_bytes(data:bytes)->str:return hashlib.sha256(data).hexdigest()
