import os
import pickle
import warnings
import numpy as np
import pandas as pd
from pathlib import Path

# Suppress benign version warnings when unpickling LinearRegression
warnings.filterwarnings("ignore", category=UserWarning)
try:
    from sklearn.exceptions import InconsistentVersionWarning
    warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
except ImportError:
    pass

class MLService:
    """
    Production-ready Machine Learning inference service.
    Guarantees strict compliance with the existing 6-feature LinearRegression model contract:
    Features: [age, sex, bmi, children, smoker, region]
    Input Shape: (1, 6)
    """

    _model = None
    _model_path = None

    # Exact categorical mapping rules
    SEX_MAPPING = {'male': 0, 'female': 1}
    SMOKER_MAPPING = {'yes': 1, 'no': 0}
    REGION_MAPPING = {
        'southeast': 0,
        'southwest': 1,
        'northeast': 2,
        'northwest': 3
    }
    FEATURE_ORDER = ['age', 'sex', 'bmi', 'children', 'smoker', 'region']

    @classmethod
    def load_model(cls, model_path=None):
        """Loads and caches the model from the specified or default file path."""
        if model_path is None:
            model_path = Path(__file__).resolve().parent.parent / "model.pkl"
        
        cls._model_path = str(model_path)
        if not os.path.exists(cls._model_path):
            raise FileNotFoundError(f"Model file not found at: {cls._model_path}")
        
        with open(cls._model_path, "rb") as f:
            cls._model = pickle.load(f)
        
        return cls._model

    @classmethod
    def get_model(cls):
        """Returns cached model, loading it if not yet initialized."""
        if cls._model is None:
            cls.load_model()
        return cls._model

    @classmethod
    def validate_inputs(cls, raw_data):
        """
        Validates raw form inputs from user.
        Returns: (cleaned_dict, error_message)
        """
        try:
            # 1. Age validation
            if 'age' not in raw_data or str(raw_data['age']).strip() == '':
                return None, "Age is required."
            age = float(raw_data['age'])
            if not (1 <= age <= 120):
                return None, "Age must be a realistic number between 1 and 120."

            # 2. Sex validation
            sex_raw = str(raw_data.get('sex', '')).strip().lower()
            if sex_raw not in cls.SEX_MAPPING:
                return None, "Please select a valid gender ('male' or 'female')."

            # 3. BMI validation
            if 'bmi' not in raw_data or str(raw_data['bmi']).strip() == '':
                return None, "BMI is required."
            bmi = float(raw_data['bmi'])
            if not (10.0 <= bmi <= 70.0):
                return None, "BMI must be a realistic value between 10.0 and 70.0."

            # 4. Children validation
            if 'children' not in raw_data or str(raw_data['children']).strip() == '':
                return None, "Number of children is required."
            children = int(raw_data['children'])
            if not (0 <= children <= 20):
                return None, "Number of children must be between 0 and 20."

            # 5. Smoker validation
            smoker_raw = str(raw_data.get('smoker', '')).strip().lower()
            if smoker_raw not in cls.SMOKER_MAPPING:
                return None, "Please select smoking status ('yes' or 'no')."

            # 6. Region validation
            region_raw = str(raw_data.get('region', '')).strip().lower()
            if region_raw not in cls.REGION_MAPPING:
                return None, "Please select a valid region ('southeast', 'southwest', 'northeast', 'northwest')."

            cleaned = {
                'age': age,
                'sex': sex_raw,
                'bmi': bmi,
                'children': children,
                'smoker': smoker_raw,
                'region': region_raw
            }
            return cleaned, None

        except (ValueError, TypeError) as e:
            return None, f"Invalid input format: {str(e)}"

    @classmethod
    def encode_features(cls, cleaned_data, as_dataframe=True):
        """
        Transforms validated inputs into the exact 6 features required by model.pkl:
        Feature vector: [age, sex, bmi, children, smoker, region]
        Shape: (1, 6)
        """
        age_val = float(cleaned_data['age'])
        sex_val = cls.SEX_MAPPING[cleaned_data['sex']]
        bmi_val = float(cleaned_data['bmi'])
        children_val = int(cleaned_data['children'])
        smoker_val = cls.SMOKER_MAPPING[cleaned_data['smoker']]
        region_val = cls.REGION_MAPPING[cleaned_data['region']]

        row_values = [[age_val, sex_val, bmi_val, children_val, smoker_val, region_val]]

        if as_dataframe:
            # Using DataFrame with matching feature names eliminates sklearn UserWarning
            return pd.DataFrame(row_values, columns=cls.FEATURE_ORDER)
        return np.array(row_values, dtype=float)

    @classmethod
    def predict(cls, cleaned_data):
        """
        Runs ML prediction using existing model.pkl.
        Returns:
            predicted_cost (float),
            formatted_text (str)
        """
        model = cls.get_model()
        features_df = cls.encode_features(cleaned_data, as_dataframe=True)
        
        # Run inference
        raw_prediction = model.predict(features_df)[0]
        predicted_cost = max(0.0, float(raw_prediction))
        
        formatted_text = f"Estimated Insurance Cost: Rs.{predicted_cost:,.2f}"
        return predicted_cost, formatted_text
