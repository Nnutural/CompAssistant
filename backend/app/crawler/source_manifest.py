from __future__ import annotations

from pydantic import Field, field_validator

from .schemas import CrawlerBaseModel
from .taxonomy import (
    ALL_DOCUMENT_SOURCE_TYPES,
    ALL_IMPLEMENTATION_STATUSES,
    ALL_SOURCE_ACCESS_STRATEGIES,
    ALL_SOURCE_CHANNELS,
    DocumentSourceType,
    SourceAccessStrategy,
    SourceChannelType,
    SourceImplementationStatus,
)


class SourceManifestEntry(CrawlerBaseModel):
    source_id: str = Field(min_length=1)
    source_type: DocumentSourceType
    source_channel: SourceChannelType
    source_name: str = Field(min_length=1)
    implementation_status: SourceImplementationStatus
    access_strategy: SourceAccessStrategy
    entrypoint: str | None = None
    description: str = Field(min_length=1)
    notes: str = ""

    @field_validator("source_id", "source_name", "description", mode="before")
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("entrypoint", "notes", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


SOURCE_MANIFEST: tuple[SourceManifestEntry, ...] = (
    SourceManifestEntry(
        source_id="moe_innovation_policy_public_web",
        source_type="national_policy",
        source_channel="public_web",
        source_name="moe_innovation_policy",
        implementation_status="implemented",
        access_strategy="static_http_source",
        entrypoint="https://www.moe.gov.cn/jyb_xwfb/s6052/moe_838/202110/t20211013_571912.html",
        description="教育部公开静态页面，作为国家政策类最小真实来源。",
        notes="通过 http_provider 获取，无登录，无动态渲染。",
    ),
    SourceManifestEntry(
        source_id="nsfc_regulation_public_web",
        source_type="law_regulation",
        source_channel="public_web",
        source_name="nsfc_regulation",
        implementation_status="implemented",
        access_strategy="static_http_source",
        entrypoint="https://www.nsfc.gov.cn/p1/2871/2873/69510.html",
        description="国家自然科学基金条例公开静态页，作为法律法规类最小真实来源。",
        notes="只抓取公开 HTML 页面。",
    ),
    SourceManifestEntry(
        source_id="social_hotspot_curated_json",
        source_type="social_hotspot",
        source_channel="manual_import",
        source_name="social_hotspot_curated",
        implementation_status="importer",
        access_strategy="structured_importer",
        entrypoint="backend/data/local_knowledge_imports/phase5h/social_hotspots.json",
        description="人工整理 JSON 热点观察，避免接入复杂热点平台抓取。",
        notes="本轮不实现微博、公众号平台抓取。",
    ),
    SourceManifestEntry(
        source_id="moe_employment_notice_public_web",
        source_type="employment_recruitment",
        source_channel="public_web",
        source_name="moe_employment_notice",
        implementation_status="implemented",
        access_strategy="static_http_source",
        entrypoint="https://www.moe.gov.cn/srcsite/A15/s3265/202411/t20241112_1162526.html",
        description="教育部公开静态就业通知页面，作为就业招聘类最小真实来源。",
        notes="保守选择公开就业通知页，不接登录型招聘平台。",
    ),
    SourceManifestEntry(
        source_id="nsfc_guide_public_web",
        source_type="fund_guide",
        source_channel="public_web",
        source_name="nsfc_original_exploration_guide",
        implementation_status="implemented",
        access_strategy="static_http_source",
        entrypoint="https://www.nsfc.gov.cn/p1/3381/2824/79214.html",
        description="国家自然科学基金公开指南/通告页面，作为基金指南类最小真实来源。",
        notes="公开静态来源。",
    ),
    SourceManifestEntry(
        source_id="moe_approved_projects_public_web",
        source_type="approved_project",
        source_channel="public_web",
        source_name="xjtu_approved_projects",
        implementation_status="implemented",
        access_strategy="static_http_source",
        entrypoint="https://jwc.xjtu.edu.cn/info/1216/4162.htm",
        description="高校公开立项/获批项目通知页面，作为获批项目类最小真实来源。",
        notes="公开静态 HTML 页面，无分页深抓。",
    ),
    SourceManifestEntry(
        source_id="competition_catalog_static",
        source_type="competition_info",
        source_channel="local_file",
        source_name="competition_catalog_static",
        implementation_status="implemented",
        access_strategy="structured_importer",
        entrypoint="backend/data/competitions.json",
        description="现有 competitions 静态 JSON 作为竞赛信息类本地来源。",
        notes="继续复用现有系统已有高质量静态数据。",
    ),
    SourceManifestEntry(
        source_id="moe_internet_plus_competition_public_web",
        source_type="competition_info",
        source_channel="public_web",
        source_name="moe_service_outsourcing_competition",
        implementation_status="implemented",
        access_strategy="static_http_source",
        entrypoint="https://www.moe.gov.cn/srcsite/A08/moe_742/s7172/s5644/201109/t20110930_171579.html",
        description="教育部公开竞赛通知页面，补充竞赛信息类公开网页来源。",
        notes="与本地 competitions.json 并存，避免仅依赖内部静态数据。",
    ),
    SourceManifestEntry(
        source_id="award_winning_works_curated_csv",
        source_type="award_winning_work",
        source_channel="manual_import",
        source_name="award_winning_works_curated",
        implementation_status="importer",
        access_strategy="structured_importer",
        entrypoint="backend/data/local_knowledge_imports/phase5h/award_winning_works.csv",
        description="人工整理获奖作品 CSV 导入。",
        notes="本轮不做外部站点自动抓取。",
    ),
    SourceManifestEntry(
        source_id="excellent_template_markdown",
        source_type="excellent_template",
        source_channel="local_file",
        source_name="excellent_template_curated",
        implementation_status="importer",
        access_strategy="file_importer",
        entrypoint="backend/data/local_knowledge_imports/phase5h/excellent_template.md",
        description="优秀模板 Markdown 导入。",
        notes="适合人工维护版本。",
    ),
    SourceManifestEntry(
        source_id="experience_sharing_text",
        source_type="experience_sharing",
        source_channel="local_file",
        source_name="experience_sharing_curated",
        implementation_status="importer",
        access_strategy="file_importer",
        entrypoint="backend/data/local_knowledge_imports/phase5h/experience_sharing.txt",
        description="经验分享 TXT 导入。",
        notes="本轮不扩展为内容社区抓取。",
    ),
    SourceManifestEntry(
        source_id="wechat_experience_article_importer",
        source_type="experience_sharing",
        source_channel="wechat_official_account",
        source_name="wechat_experience_article",
        implementation_status="importer",
        access_strategy="manual_curated_source",
        entrypoint="backend/data/local_knowledge_imports/phase5h/wechat_article_experience.md",
        description="微信公众号文章导入器占位，只接收用户已有文章文本/Markdown。",
        notes="明确不实现公众号自动抓取和绕过。",
    ),
)


def list_source_manifest_entries() -> list[SourceManifestEntry]:
    return [entry.model_copy(deep=True) for entry in SOURCE_MANIFEST]


def get_content_categories() -> tuple[DocumentSourceType, ...]:
    return ALL_DOCUMENT_SOURCE_TYPES


def get_source_channels() -> tuple[SourceChannelType, ...]:
    return ALL_SOURCE_CHANNELS


def get_implementation_statuses() -> tuple[SourceImplementationStatus, ...]:
    return ALL_IMPLEMENTATION_STATUSES


def get_access_strategies() -> tuple[SourceAccessStrategy, ...]:
    return ALL_SOURCE_ACCESS_STRATEGIES
