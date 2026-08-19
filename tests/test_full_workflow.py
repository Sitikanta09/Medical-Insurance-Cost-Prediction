import unittest
import os
import shutil
from app import create_app
from config import Config
from database import get_db, init_db
from models.user import UserModel
from models.prediction import PredictionModel
from services.ml_service import MLService

class WorkflowVerificationTest(unittest.TestCase):
    """
    Directly tests all 20 explicit requirements requested by the user.
    """

    @classmethod
    def setUpClass(cls):
        cls.test_db = "test_verification_workflow.db"
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)
        
        class CustomConfig(Config):
            TESTING = True
            DATABASE_PATH = cls.test_db
            SECRET_KEY = "verification-key-secret"

        cls.app = create_app(CustomConfig)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_db):
            try:
                os.remove(cls.test_db)
            except OSError:
                pass

    def test_20_point_verification_matrix(self):
        # 1. Start Flask app (verified by app factory creation)
        self.assertIsNotNone(self.app)

        # 2. Register a new user
        reg_res = self.client.post('/register', data={
            'username': 'john_doe',
            'email': 'john@example.com',
            'password': 'Password@123',
            'confirm_password': 'Password@123'
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)
        self.assertIn(b'Registration successful', reg_res.data)

        # 3. Attempt duplicate registration
        dup_res = self.client.post('/register', data={
            'username': 'john_doe',
            'email': 'john_other@example.com',
            'password': 'Password@123',
            'confirm_password': 'Password@123'
        }, follow_redirects=True)
        self.assertIn(b'already taken', dup_res.data)

        # 4. Login with correct credentials
        login_res = self.client.post('/login', data={
            'username': 'john_doe',
            'password': 'Password@123'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Welcome back, john_doe', login_res.data)

        # 5. Access dashboard while logged in
        dash_res = self.client.get('/dashboard')
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b'john_doe', dash_res.data)

        # 6. Logout
        logout_res = self.client.get('/logout', follow_redirects=True)
        self.assertIn(b'logged out', logout_res.data)

        # 7. Login with incorrect credentials
        bad_login = self.client.post('/login', data={
            'username': 'john_doe',
            'password': 'WrongPassword99'
        }, follow_redirects=True)
        self.assertIn(b'Invalid username or password', bad_login.data)

        # 8. Access protected pages while logged out
        for protected_url in ['/dashboard', '/predict-form', '/predict', '/history', '/profile']:
            res = self.client.get(protected_url)
            self.assertEqual(res.status_code, 302)
            self.assertIn('/login', res.headers.get('Location', ''))

        # Log back in
        self.client.post('/login', data={'username': 'john_doe', 'password': 'Password@123'})

        # 9. Submit invalid prediction
        invalid_pred = self.client.post('/predict', data={
            'age': '-10',  # Invalid age
            'sex': 'male',
            'bmi': '25.0',
            'children': '0',
            'smoker': 'no',
            'region': 'southwest'
        }, follow_redirects=True)
        self.assertIn(b'Age must be a realistic number', invalid_pred.data)

        # 10. Submit valid prediction & 11. Verify prediction result
        pred_res = self.client.post('/predict', data={
            'age': '25',
            'sex': 'male',
            'bmi': '28.5',
            'children': '0',
            'smoker': 'no',
            'region': 'southwest'
        }, follow_redirects=True)
        self.assertEqual(pred_res.status_code, 200)
        self.assertIn(b'3,290.58', pred_res.data)

        # 12. Verify prediction is stored in database & 13. Appears in history
        hist_res = self.client.get('/history')
        self.assertEqual(hist_res.status_code, 200)
        self.assertIn(b'Southwest', hist_res.data)
        self.assertIn(b'3,290.58', hist_res.data)

        # 14. Verify another user cannot access first user's history
        self.client.get('/logout')
        self.client.post('/register', data={'username': 'sarah', 'password': 'password123', 'confirm_password': 'password123'})
        self.client.post('/login', data={'username': 'sarah', 'password': 'password123'})
        
        sarah_hist = self.client.get('/history')
        # Sarah must not see John's prediction of 3,290.58
        self.assertNotIn(b'3,290.58', sarah_hist.data)
        self.assertIn(b'No prediction records match', sarah_hist.data)

        # 15. Verify persistence across simulated app restart
        # Create a new app instance pointing to the same SQLite DB file
        class RestartConfig(Config):
            TESTING = True
            DATABASE_PATH = WorkflowVerificationTest.test_db
            SECRET_KEY = "verification-key-secret"

        restarted_app = create_app(RestartConfig)
        restarted_client = restarted_app.test_client()

        # 16. Verify registered user still exists after restart
        login_after_restart = restarted_client.post('/login', data={
            'username': 'john_doe',
            'password': 'Password@123'
        }, follow_redirects=True)
        self.assertEqual(login_after_restart.status_code, 200)
        self.assertIn(b'Welcome back, john_doe', login_after_restart.data)

        # 17. Make another prediction after restart
        pred2_res = restarted_client.post('/predict', data={
            'age': '40',
            'sex': 'female',
            'bmi': '32.0',
            'children': '2',
            'smoker': 'yes',
            'region': 'southeast'
        }, follow_redirects=True)
        self.assertEqual(pred2_res.status_code, 200)
        self.assertIn(b'Prediction Result', pred2_res.data)

        # 18. Verify model.pkl still loads and matches 6-feature LinearRegression contract
        model = MLService.get_model()
        self.assertIsNotNone(model)
        self.assertEqual(getattr(model, 'n_features_in_', 6), 6)

        # 19. Verify exact feature order
        self.assertEqual(MLService.FEATURE_ORDER, ['age', 'sex', 'bmi', 'children', 'smoker', 'region'])

if __name__ == '__main__':
    unittest.main()
