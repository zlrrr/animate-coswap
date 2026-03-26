"""
Unit tests for FaceMappingService

Tests face mapping logic in isolation using mocks and in-memory SQLite.
No dependency on PostgreSQL or InsightFace models.
"""

import pytest
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import Base, Image, Template, TemplatePreprocessing
from app.services.face_mapping import FaceMappingService, FaceMappingError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """In-memory SQLite session with all tables created."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def seed_template_with_faces(db_session):
    """
    Helper that inserts an Image, Template, and TemplatePreprocessing row
    and returns the template id.
    """
    def _seed(face_data):
        img = Image(filename="tpl.png", storage_path="/tmp/tpl.png")
        db_session.add(img)
        db_session.flush()

        tpl = Template(name="test", original_image_id=img.id)
        db_session.add(tpl)
        db_session.flush()

        pp = TemplatePreprocessing(
            template_id=tpl.id,
            original_image_id=img.id,
            faces_detected=len(face_data),
            face_data=face_data,
            preprocessing_status="completed",
        )
        db_session.add(pp)
        db_session.commit()
        return tpl.id

    return _seed


# ---------------------------------------------------------------------------
# 1. generate_default_mapping
# ---------------------------------------------------------------------------

class TestGenerateDefaultMapping:
    """Tests for FaceMappingService.generate_default_mapping"""

    def test_fallback_when_no_preprocessing(self, db_session):
        """Without preprocessing data, returns the simple fallback mapping."""
        # Template with no preprocessing row at all
        img = Image(filename="x.png", storage_path="/tmp/x.png")
        db_session.add(img)
        db_session.flush()
        tpl = Template(name="bare", original_image_id=img.id)
        db_session.add(tpl)
        db_session.commit()

        mappings = FaceMappingService.generate_default_mapping(tpl.id, db_session)

        assert len(mappings) == 2
        assert mappings[0] == {
            "source_photo": "husband",
            "source_face_index": 0,
            "target_face_index": 0,
        }
        assert mappings[1] == {
            "source_photo": "wife",
            "source_face_index": 0,
            "target_face_index": 1,
        }

    def test_fallback_when_face_data_is_none(self, db_session):
        """Preprocessing row exists but face_data is None -> fallback."""
        img = Image(filename="x.png", storage_path="/tmp/x.png")
        db_session.add(img)
        db_session.flush()
        tpl = Template(name="t", original_image_id=img.id)
        db_session.add(tpl)
        db_session.flush()
        pp = TemplatePreprocessing(
            template_id=tpl.id,
            original_image_id=img.id,
            faces_detected=0,
            face_data=None,
            preprocessing_status="completed",
        )
        db_session.add(pp)
        db_session.commit()

        mappings = FaceMappingService.generate_default_mapping(tpl.id, db_session)
        assert len(mappings) == 2
        assert mappings[0]["source_photo"] == "husband"
        assert mappings[1]["source_photo"] == "wife"

    def test_gender_based_mapping(self, db_session, seed_template_with_faces):
        """Male faces mapped to husband, female faces mapped to wife."""
        face_data = [
            {"index": 0, "gender": "male"},
            {"index": 1, "gender": "female"},
            {"index": 2, "gender": "male"},
        ]
        tpl_id = seed_template_with_faces(face_data)

        mappings = FaceMappingService.generate_default_mapping(tpl_id, db_session)

        husband_targets = [
            m["target_face_index"] for m in mappings if m["source_photo"] == "husband"
        ]
        wife_targets = [
            m["target_face_index"] for m in mappings if m["source_photo"] == "wife"
        ]

        assert sorted(husband_targets) == [0, 2]
        assert wife_targets == [1]

    def test_all_male_faces(self, db_session, seed_template_with_faces):
        """When all faces are male, only husband mappings are generated."""
        face_data = [
            {"index": 0, "gender": "male"},
            {"index": 1, "gender": "male"},
        ]
        tpl_id = seed_template_with_faces(face_data)

        mappings = FaceMappingService.generate_default_mapping(tpl_id, db_session)

        assert all(m["source_photo"] == "husband" for m in mappings)
        assert len(mappings) == 2

    def test_all_female_faces(self, db_session, seed_template_with_faces):
        """When all faces are female, only wife mappings are generated."""
        face_data = [
            {"index": 0, "gender": "female"},
            {"index": 1, "gender": "female"},
        ]
        tpl_id = seed_template_with_faces(face_data)

        mappings = FaceMappingService.generate_default_mapping(tpl_id, db_session)

        assert all(m["source_photo"] == "wife" for m in mappings)
        assert len(mappings) == 2

    def test_unknown_gender_ignored(self, db_session, seed_template_with_faces):
        """Faces with unknown gender produce no mappings."""
        face_data = [
            {"index": 0, "gender": "unknown"},
            {"index": 1, "gender": "male"},
        ]
        tpl_id = seed_template_with_faces(face_data)

        mappings = FaceMappingService.generate_default_mapping(tpl_id, db_session)

        assert len(mappings) == 1
        assert mappings[0]["target_face_index"] == 1

    def test_empty_face_data_list(self, db_session, seed_template_with_faces):
        """Empty face_data list is falsy, so the service returns fallback mapping."""
        tpl_id = seed_template_with_faces([])

        mappings = FaceMappingService.generate_default_mapping(tpl_id, db_session)
        # [] is falsy -> hits the "not preprocessing.face_data" branch -> fallback
        assert len(mappings) == 2
        assert mappings[0]["source_photo"] == "husband"
        assert mappings[1]["source_photo"] == "wife"

    def test_nonexistent_template(self, db_session):
        """Non-existent template id returns fallback mapping."""
        mappings = FaceMappingService.generate_default_mapping(99999, db_session)
        assert len(mappings) == 2


# ---------------------------------------------------------------------------
# 2. validate_mapping
# ---------------------------------------------------------------------------

class TestValidateMapping:
    """Tests for FaceMappingService.validate_mapping"""

    def test_valid_husband_mapping(self):
        m = {"source_photo": "husband", "source_face_index": 0, "target_face_index": 0}
        assert FaceMappingService.validate_mapping(m) is True

    def test_valid_wife_mapping(self):
        m = {"source_photo": "wife", "source_face_index": 0, "target_face_index": 1}
        assert FaceMappingService.validate_mapping(m) is True

    def test_missing_source_photo(self):
        with pytest.raises(FaceMappingError, match="Missing required field: source_photo"):
            FaceMappingService.validate_mapping(
                {"source_face_index": 0, "target_face_index": 0}
            )

    def test_missing_source_face_index(self):
        with pytest.raises(FaceMappingError, match="Missing required field: source_face_index"):
            FaceMappingService.validate_mapping(
                {"source_photo": "husband", "target_face_index": 0}
            )

    def test_missing_target_face_index(self):
        with pytest.raises(FaceMappingError, match="Missing required field: target_face_index"):
            FaceMappingService.validate_mapping(
                {"source_photo": "husband", "source_face_index": 0}
            )

    def test_invalid_source_photo_value(self):
        with pytest.raises(FaceMappingError, match="Invalid source_photo"):
            FaceMappingService.validate_mapping(
                {"source_photo": "child", "source_face_index": 0, "target_face_index": 0}
            )

    def test_negative_source_face_index(self):
        with pytest.raises(FaceMappingError, match="Invalid source_face_index"):
            FaceMappingService.validate_mapping(
                {"source_photo": "husband", "source_face_index": -1, "target_face_index": 0}
            )

    def test_negative_target_face_index(self):
        with pytest.raises(FaceMappingError, match="Invalid target_face_index"):
            FaceMappingService.validate_mapping(
                {"source_photo": "husband", "source_face_index": 0, "target_face_index": -1}
            )

    def test_non_integer_source_index(self):
        with pytest.raises(FaceMappingError, match="Invalid source_face_index"):
            FaceMappingService.validate_mapping(
                {"source_photo": "husband", "source_face_index": "zero", "target_face_index": 0}
            )

    def test_non_integer_target_index(self):
        with pytest.raises(FaceMappingError, match="Invalid target_face_index"):
            FaceMappingService.validate_mapping(
                {"source_photo": "wife", "source_face_index": 0, "target_face_index": 1.5}
            )

    def test_high_indices_still_valid(self):
        """High indices are valid (only trigger a warning, no error)."""
        m = {"source_photo": "husband", "source_face_index": 99, "target_face_index": 99}
        assert FaceMappingService.validate_mapping(m) is True

    def test_empty_dict_raises(self):
        with pytest.raises(FaceMappingError, match="Missing required field"):
            FaceMappingService.validate_mapping({})


# ---------------------------------------------------------------------------
# 2b. validate_mappings (list-level)
# ---------------------------------------------------------------------------

class TestValidateMappings:
    """Tests for FaceMappingService.validate_mappings"""

    def test_valid_list(self):
        mappings = [
            {"source_photo": "husband", "source_face_index": 0, "target_face_index": 0},
            {"source_photo": "wife", "source_face_index": 0, "target_face_index": 1},
        ]
        assert FaceMappingService.validate_mappings(mappings) is True

    def test_not_a_list(self):
        with pytest.raises(FaceMappingError, match="must be a list"):
            FaceMappingService.validate_mappings("not a list")

    def test_empty_list(self):
        with pytest.raises(FaceMappingError, match="cannot be empty"):
            FaceMappingService.validate_mappings([])

    def test_invalid_item_reports_index(self):
        mappings = [
            {"source_photo": "husband", "source_face_index": 0, "target_face_index": 0},
            {"source_photo": "bad", "source_face_index": 0, "target_face_index": 0},
        ]
        with pytest.raises(FaceMappingError, match="index 1"):
            FaceMappingService.validate_mappings(mappings)


# ---------------------------------------------------------------------------
# 3. convert_to_dict
# ---------------------------------------------------------------------------

class TestConvertToDict:
    """Tests for FaceMappingService.convert_to_dict"""

    def test_dict_passthrough(self):
        data = [{"a": 1}, {"b": 2}]
        assert FaceMappingService.convert_to_dict(data) == data

    def test_pydantic_like_objects(self):
        """Objects with a .dict() method get serialised."""
        obj = MagicMock()
        obj.dict.return_value = {"source_photo": "husband", "source_face_index": 0}

        result = FaceMappingService.convert_to_dict([obj])
        assert result == [{"source_photo": "husband", "source_face_index": 0}]
        obj.dict.assert_called_once()

    def test_other_iterable_converted_via_dict(self):
        """Fallback: objects castable via dict() (e.g. list of tuples)."""
        pairs = [("source_photo", "wife"), ("source_face_index", 0)]
        result = FaceMappingService.convert_to_dict([pairs])
        assert result == [{"source_photo": "wife", "source_face_index": 0}]

    def test_empty_list(self):
        assert FaceMappingService.convert_to_dict([]) == []

    def test_mixed_types(self):
        obj = MagicMock()
        obj.dict.return_value = {"x": 1}
        raw = {"y": 2}

        result = FaceMappingService.convert_to_dict([obj, raw])
        assert result == [{"x": 1}, {"y": 2}]


# ---------------------------------------------------------------------------
# 4. Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge-case scenarios across the service."""

    def test_face_data_missing_index_key(self, db_session, seed_template_with_faces):
        """Face entries without an explicit 'index' key should still work."""
        face_data = [
            {"gender": "male"},   # no 'index' key
            {"gender": "female"},
        ]
        tpl_id = seed_template_with_faces(face_data)

        mappings = FaceMappingService.generate_default_mapping(tpl_id, db_session)
        # The code falls back to len(male)+len(female) as the index
        assert len(mappings) == 2

    def test_face_data_missing_gender_key(self, db_session, seed_template_with_faces):
        """Face entries without a 'gender' key are treated as unknown -> skipped."""
        face_data = [{"index": 0}]
        tpl_id = seed_template_with_faces(face_data)

        mappings = FaceMappingService.generate_default_mapping(tpl_id, db_session)
        assert mappings == []

    def test_validate_mapping_with_zero_indices(self):
        """Zero is a valid face index."""
        m = {"source_photo": "husband", "source_face_index": 0, "target_face_index": 0}
        assert FaceMappingService.validate_mapping(m) is True


# ---------------------------------------------------------------------------
# 5. FaceMappingError exception
# ---------------------------------------------------------------------------

class TestFaceMappingError:
    """Tests for the FaceMappingError exception class."""

    def test_is_exception(self):
        assert issubclass(FaceMappingError, Exception)

    def test_message_preserved(self):
        err = FaceMappingError("something went wrong")
        assert str(err) == "something went wrong"

    def test_can_be_caught_as_exception(self):
        with pytest.raises(Exception):
            raise FaceMappingError("boom")


# ---------------------------------------------------------------------------
# 6. apply_mapping_to_task
# ---------------------------------------------------------------------------

class TestApplyMappingToTask:
    """Tests for FaceMappingService.apply_mapping_to_task"""

    def test_custom_mappings_used_when_provided(self, db_session):
        custom = [
            {"source_photo": "husband", "source_face_index": 0, "target_face_index": 2},
            {"source_photo": "wife", "source_face_index": 0, "target_face_index": 3},
        ]
        result = FaceMappingService.apply_mapping_to_task(
            husband_photo_id=1,
            wife_photo_id=2,
            template_id=1,
            use_default_mapping=True,
            custom_mappings=custom,
            db=db_session,
        )
        assert result == custom

    def test_custom_mappings_validated(self, db_session):
        bad = [{"source_photo": "nope", "source_face_index": 0, "target_face_index": 0}]
        with pytest.raises(FaceMappingError, match="Invalid source_photo"):
            FaceMappingService.apply_mapping_to_task(
                husband_photo_id=1,
                wife_photo_id=2,
                template_id=1,
                use_default_mapping=False,
                custom_mappings=bad,
                db=db_session,
            )

    def test_default_mapping_generated(self, db_session, seed_template_with_faces):
        face_data = [
            {"index": 0, "gender": "male"},
            {"index": 1, "gender": "female"},
        ]
        tpl_id = seed_template_with_faces(face_data)

        result = FaceMappingService.apply_mapping_to_task(
            husband_photo_id=1,
            wife_photo_id=2,
            template_id=tpl_id,
            use_default_mapping=True,
            custom_mappings=None,
            db=db_session,
        )
        assert len(result) == 2
        assert result[0]["source_photo"] == "husband"
        assert result[1]["source_photo"] == "wife"

    def test_fallback_when_no_mapping_specified(self, db_session):
        result = FaceMappingService.apply_mapping_to_task(
            husband_photo_id=1,
            wife_photo_id=2,
            template_id=1,
            use_default_mapping=False,
            custom_mappings=None,
            db=db_session,
        )
        assert len(result) == 2
        assert result[0]["target_face_index"] == 0
        assert result[1]["target_face_index"] == 1
