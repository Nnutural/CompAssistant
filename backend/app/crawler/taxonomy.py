from __future__ import annotations

from typing import Literal


DocumentSourceType = Literal[
    "national_policy",
    "law_regulation",
    "social_hotspot",
    "employment_recruitment",
    "fund_guide",
    "approved_project",
    "competition_info",
    "award_winning_work",
    "excellent_template",
    "experience_sharing",
]

SourceChannelType = Literal[
    "public_web",
    "wechat_official_account",
    "manual_import",
    "local_file",
]

SourceImplementationStatus = Literal["implemented", "importer", "placeholder", "planned"]

SourceAccessStrategy = Literal[
    "static_http_source",
    "file_importer",
    "structured_importer",
    "placeholder_source",
    "manual_curated_source",
]


ALL_DOCUMENT_SOURCE_TYPES: tuple[DocumentSourceType, ...] = (
    "national_policy",
    "law_regulation",
    "social_hotspot",
    "employment_recruitment",
    "fund_guide",
    "approved_project",
    "competition_info",
    "award_winning_work",
    "excellent_template",
    "experience_sharing",
)

ALL_SOURCE_CHANNELS: tuple[SourceChannelType, ...] = (
    "public_web",
    "wechat_official_account",
    "manual_import",
    "local_file",
)

ALL_IMPLEMENTATION_STATUSES: tuple[SourceImplementationStatus, ...] = (
    "implemented",
    "importer",
    "placeholder",
    "planned",
)

ALL_SOURCE_ACCESS_STRATEGIES: tuple[SourceAccessStrategy, ...] = (
    "static_http_source",
    "file_importer",
    "structured_importer",
    "placeholder_source",
    "manual_curated_source",
)

SOURCE_TYPE_LABELS: dict[DocumentSourceType, str] = {
    "national_policy": "国家政策",
    "law_regulation": "法律法规",
    "social_hotspot": "社会热点",
    "employment_recruitment": "就业招聘",
    "fund_guide": "基金指南",
    "approved_project": "获批项目",
    "competition_info": "竞赛信息",
    "award_winning_work": "获奖作品",
    "excellent_template": "优秀模板",
    "experience_sharing": "经验分享",
}

SOURCE_CHANNEL_LABELS: dict[SourceChannelType, str] = {
    "public_web": "互联网公开网页",
    "wechat_official_account": "微信公众号",
    "manual_import": "手动导入",
    "local_file": "本地文件",
}

IMPLEMENTATION_STATUS_LABELS: dict[SourceImplementationStatus, str] = {
    "implemented": "已实现",
    "importer": "导入器",
    "placeholder": "占位",
    "planned": "计划中",
}

