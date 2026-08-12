import enum


class OutcomeEnum(str, enum.Enum):
    admitted = "admitted"
    cirp_ongoing = "cirp_ongoing"
    resolution_approved = "resolution_approved"
    liquidation = "liquidation"
    dissolved = "dissolved"
    withdrawn = "withdrawn"
    unclassified = "unclassified"


class ProcessingStatusEnum(str, enum.Enum):
    discovered = "discovered"
    downloaded = "downloaded"
    text_extracted = "text_extracted"
    scanned_skipped = "scanned_skipped"
    ocr_extracted = "ocr_extracted"
    extracted = "extracted"
    failed = "failed"


class CreditorTypeEnum(str, enum.Enum):
    financial = "financial"
    operational = "operational"
    corporate_applicant = "corporate_applicant"


class LinkReviewStatusEnum(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
