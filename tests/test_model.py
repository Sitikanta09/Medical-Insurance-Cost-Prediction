import unittest
import numpy as np
from services.ml_service import MLService

class TestMLModelIntegration(unittest.TestCase):
    """
    Verifies that model.pkl is safely integrated and adheres to the strict 6-feature contract:
    [age, sex, bmi, children, smoker, region]
    """

    def setUp(self):
        self.model = MLService.get_model()

    def test_model_loaded(self):
        """Verify model is loaded and is not None."""
        self.assertIsNotNone(self.model)
        self.assertEqual(getattr(self.model, 'n_features_in_', 6), 6)

    def test_feature_encoding_and_contract(self):
        """Verify feature encoding maps correctly into shape (1, 6)."""
        raw_data = {
            'age': '25',
            'sex': 'male',
            'bmi': '28.5',
            'children': '0',
            'smoker': 'no',
            'region': 'southwest'
        }
        cleaned, err = MLService.validate_inputs(raw_data)
        self.assertIsNone(err)
        self.assertIsNotNone(cleaned)

        feature_matrix = MLService.encode_features(cleaned)
        self.assertEqual(feature_matrix.shape, (1, 6))
        # Expected: [25.0, 0, 28.5, 0, 0, 1]
        np.testing.assert_array_equal(feature_matrix, [[25.0, 0.0, 28.5, 0.0, 0.0, 1.0]])

    def test_baseline_prediction_exact_match(self):
        """
        Verify that prediction on baseline test input [25, male(0), 28.5, 0, no(0), southwest(1)]
        produces the exact expected value (~3290.58).
        """
        cleaned_data = {
            'age': 25.0,
            'sex': 'male',
            'bmi': 28.5,
            'children': 0,
            'smoker': 'no',
            'region': 'southwest'
        }
        cost, formatted_text = MLService.predict(cleaned_data)
        self.assertAlmostEqual(cost, 3290.5821709266347, places=3)
        self.assertIn("3,290.58", formatted_text)

    def test_categorical_mappings(self):
        """Verify all categories map to distinct expected integer codes."""
        # Smoker yes -> 1, no -> 0
        self.assertEqual(MLService.SMOKER_MAPPING['yes'], 1)
        self.assertEqual(MLService.SMOKER_MAPPING['no'], 0)

        # Sex male -> 0, female -> 1
        self.assertEqual(MLService.SEX_MAPPING['male'], 0)
        self.assertEqual(MLService.SEX_MAPPING['female'], 1)

        # Region mappings
        self.assertEqual(MLService.REGION_MAPPING['southeast'], 0)
        self.assertEqual(MLService.REGION_MAPPING['southwest'], 1)
        self.assertEqual(MLService.REGION_MAPPING['northeast'], 2)
        self.assertEqual(MLService.REGION_MAPPING['northwest'], 3)

    def test_invalid_input_validation(self):
        """Verify validation catches out-of-bound or invalid values."""
        # Age negative
        _, err = MLService.validate_inputs({'age': '-5', 'sex': 'male', 'bmi': '25', 'children': '0', 'smoker': 'no', 'region': 'southwest'})
        self.assertIsNotNone(err)

        # BMI out of range
        _, err = MLService.validate_inputs({'age': '30', 'sex': 'male', 'bmi': '5', 'children': '0', 'smoker': 'no', 'region': 'southwest'})
        self.assertIsNotNone(err)

        # Invalid region
        _, err = MLService.validate_inputs({'age': '30', 'sex': 'male', 'bmi': '25', 'children': '0', 'smoker': 'no', 'region': 'antarctica'})
        self.assertIsNotNone(err)

if __name__ == '__main__':
    unittest.main()
