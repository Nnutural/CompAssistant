import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.crawler.importers import FileDocumentImporter, StructuredDataImporter, WeChatArticleImporter  # noqa: E402
from app.crawler.pipelines.normalize_pipeline import NormalizePipeline  # noqa: E402


IMPORT_ROOT = REPO_ROOT / "backend" / "data" / "local_knowledge_imports" / "phase5h"


class ImporterTests(unittest.TestCase):
    def test_structured_importer_supports_json_and_csv(self) -> None:
        importer = StructuredDataImporter()
        pipeline = NormalizePipeline()

        social_docs = importer.import_file(
            IMPORT_ROOT / "social_hotspots.json",
            source_type="social_hotspot",
            source_name="social_hotspot_curated",
            source_channel="manual_import",
            implementation_status="importer",
        )
        award_docs = importer.import_file(
            IMPORT_ROOT / "award_winning_works.csv",
            source_type="award_winning_work",
            source_name="award_winning_works_curated",
            source_channel="manual_import",
            implementation_status="importer",
        )

        social_normalized = pipeline.run(social_docs[0])
        award_normalized = pipeline.run(award_docs[0])

        self.assertEqual(social_docs[0].source_channel, "manual_import")
        self.assertEqual(social_normalized.source_type, "social_hotspot")
        self.assertEqual(award_normalized.source_type, "award_winning_work")
        self.assertIn("innovation", award_normalized.tags)

    def test_file_and_wechat_importers_flow_into_normalization(self) -> None:
        file_importer = FileDocumentImporter()
        wechat_importer = WeChatArticleImporter(file_importer=file_importer, structured_importer=StructuredDataImporter())
        pipeline = NormalizePipeline()

        template_docs = file_importer.import_file(
            IMPORT_ROOT / "excellent_template.md",
            source_type="excellent_template",
            source_name="excellent_template_curated",
            source_channel="local_file",
            implementation_status="importer",
        )
        wechat_docs = wechat_importer.import_article(
            IMPORT_ROOT / "wechat_article_experience.md",
            source_type="experience_sharing",
            source_name="wechat_experience_article",
        )

        template_normalized = pipeline.run(template_docs[0])
        wechat_normalized = pipeline.run(wechat_docs[0])

        self.assertEqual(template_normalized.title, "省级竞赛立项书模板")
        self.assertEqual(wechat_docs[0].source_channel, "wechat_official_account")
        self.assertEqual(wechat_normalized.source_channel, "wechat_official_account")
        self.assertEqual(wechat_normalized.implementation_status, "importer")


if __name__ == "__main__":
    unittest.main()
