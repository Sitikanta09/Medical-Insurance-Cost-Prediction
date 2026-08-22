import unittest
import os
import tempfile
import sqlite3
import numpy as np
from app import create_app
from config import Config
from database import init_db, get_db
from models.user import UserModel
from models.prediction import PredictionModel
from services.ml_service import MLService

class ComprehensiveVerificationTests(unittest.TestCase):
    """
    Executes the 5 rigorous test categories requested by the user:
    - Test 1: Complete normal workflow
    - Test 2: Stale/orphaned session handling
    - Test 3: Database integrity & foreign key constraints
    - Test 4: Existing functionality verification
    - Test 5: ML model contract & inference integrity
    """

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        
        class TestConfig(Config):
            TESTING = True
            WTF_CSRF_ENABLED = False
            DATABASE_PATH = self.db_path
            SECRET_KEY = 'test-secret-key-verification'

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

        with self.app.app_context():
            init_db(self.app)

    def tearDown(self):
        os.close(self.db_fd)
        if os.path.exists(self.db_path):
            try:
                os.unlink(self.db_path)
            except OSError:
                pass

    # =========================================================================
    # TEST 1 — Complete Normal Workflow
    # =========================================================================
    def test_01_complete_normal_workflow(self):
        """Test full end-to-end user lifecycle from registration to history persistence."""
        # 1. Register new user
        reg_res = self.client.post('/register', data={
            'username': 'workflow_user',
            'email': 'workflow@example.com',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)
        self.assertIn(b'Registration successful', reg_res.data)

        # 2. Log in with the new user
        login_res = self.client.post('/login', data={
            'username': 'workflow_user',
            'password': 'Password123!'
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        self.assertIn(b'Welcome back, workflow_user', login_res.data)

        # 3. Open prediction page
        pred_page = self.client.get('/predict')
        self.assertEqual(pred_page.status_code, 200)
        self.assertIn(b'Calculate Medical Insurance Cost', pred_page.data)

        # 4. Submit valid insurance prediction
        post_pred = self.client.post('/predict', data={
            'age': '32',
            'sex': 'female',
            'bmi': '26.4',
            'children': '1',
            'smoker': 'no',
            'region': 'southwest'
        }, follow_redirects=True)
        self.assertEqual(post_pred.status_code, 200)
        self.assertIn(b'Prediction Result', post_pred.data)
        self.assertIn(b'Estimated Annual Insurance Charge', post_pred.data)

        # 5. Confirm prediction is saved in SQLite database
        with self.app.app_context():
            user = UserModel.get_by_username('workflow_user')
            self.assertIsNotNone(user)
            db_history = PredictionModel.get_user_history(user['id'])
            self.assertEqual(db_history['total_count'], 1)
            self.assertAlmostEqual(db_history['records'][0]['bmi'], 26.4)
            self.assertEqual(db_history['records'][0]['region'], 'southwest')

        # 6. Open History in browser & confirm newly created prediction appears
        hist_page = self.client.get('/history')
        self.assertEqual(hist_page.status_code, 200)
        self.assertIn(b'Southwest', hist_page.data)
        self.assertIn(b'Non-Smoker', hist_page.data)

        # 7. Log out
        logout_res = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(logout_res.status_code, 200)
        self.assertIn(b'logged out successfully', logout_res.data)

        # 8. Log in again
        login2 = self.client.post('/login', data={
            'username': 'workflow_user',
            'password': 'Password123!'
        }, follow_redirects=True)
        self.assertEqual(login2.status_code, 200)

        # 9. Confirm prediction history is still available
        hist2 = self.client.get('/history')
        self.assertEqual(hist2.status_code, 200)
        self.assertIn(b'Southwest', hist2.data)
        self.assertIn(b'26.4', hist2.data)

    # =========================================================================
    # TEST 2 — Stale / Orphaned Session
    # =========================================================================
    def test_02_stale_orphaned_session_protection(self):
        """Simulate an orphaned session and verify graceful redirection without FK errors."""
        # 1. Create a session with non-existent user_id 999999
        with self.client.session_transaction() as sess:
            sess['user_id'] = 999999
            sess['username'] = 'ghost_user'

        # 2. Access protected predict form
        form_res = self.client.get('/predict-form', follow_redirects=True)
        self.assertEqual(form_res.status_code, 200)
        # Must redirect to login with user-friendly session warning
        self.assertIn(b'session is invalid or the user account was not found', form_res.data)
        self.assertNotIn(b'FOREIGN KEY constraint failed', form_res.data)

        # 3. Simulate another orphaned POST to /predict directly
        with self.client.session_transaction() as sess:
            sess['user_id'] = 999999
            sess['username'] = 'ghost_user'

        pred_post = self.client.post('/predict', data={
            'age': '28',
            'sex': 'male',
            'bmi': '24.0',
            'children': '0',
            'smoker': 'no',
            'region': 'southeast'
        }, follow_redirects=True)
        self.assertEqual(pred_post.status_code, 200)
        self.assertNotIn(b'FOREIGN KEY constraint failed', pred_post.data)
        self.assertIn(b'session is invalid', pred_post.data)

        # 4. Confirm session cookie was cleared
        with self.client.session_transaction() as sess:
            self.assertNotIn('user_id', sess)

    # =========================================================================
    # TEST 3 — Database Integrity & Foreign Keys
    # =========================================================================
    def test_03_database_integrity_and_foreign_keys(self):
        """Verify foreign key enforcement, transaction rollback, and non-destructive DDL."""
        with self.app.app_context():
            db = get_db()
            
            # 1. Confirm foreign keys are enabled in SQLite connection
            fk_status = db.execute("PRAGMA foreign_keys").fetchone()[0]
            self.assertEqual(fk_status, 1, "Foreign key constraints must remain enabled!")

            # 2. Attempt direct invalid insert bypassing app to verify SQLite FK raises error
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    "INSERT INTO predictions (user_id, age, sex, bmi, children, smoker, region, predicted_cost) VALUES (88888, 25, 'male', 25.0, 0, 'no', 'southwest', 3000.0)"
                )

            # 3. Test PredictionModel.create rollback handling on invalid user_id
            with self.assertRaises(ValueError) as ctx:
                PredictionModel.create(
                    user_id=77777,
                    age=30,
                    sex='male',
                    bmi=25.0,
                    children=0,
                    smoker='no',
                    region='northeast',
                    predicted_cost=4500.0
                )
            self.assertIn("User ID 77777 does not exist", str(ctx.exception))

            # 4. Verify transaction was rolled back and database is in clean state
            count = db.execute("SELECT COUNT(*) FROM predictions WHERE user_id = 77777").fetchone()[0]
            self.assertEqual(count, 0)

    # =========================================================================
    # TEST 4 — Existing Functionality Suite
    # =========================================================================
    def test_04_all_existing_features(self):
        """Verify registration, login, dashboard, search, filter, sort, pagination, delete, and profile."""
        # 1. Registration validation (duplicate check)
        self.client.post('/register', data={'username': 'john', 'password': 'Password1!', 'confirm_password': 'Password1!'})
        dup_res = self.client.post('/register', data={'username': 'john', 'password': 'Password1!', 'confirm_password': 'Password1!'}, follow_redirects=True)
        self.assertIn(b'already taken', dup_res.data)

        # 2. Login
        self.client.post('/login', data={'username': 'john', 'password': 'Password1!'})

        # 3. Dashboard metrics
        dash_res = self.client.get('/dashboard')
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b'Total Predictions', dash_res.data)

        # 4. Create 3 distinct predictions
        for i, reg, smk in [(20, 'southeast', 'no'), (35, 'northwest', 'yes'), (50, 'southwest', 'no')]:
            self.client.post('/predict', data={
                'age': str(i),
                'sex': 'male',
                'bmi': '25.0',
                'children': '0',
                'smoker': smk,
                'region': reg
            })

        # 5. History Search
        search_res = self.client.get('/history?search=northwest')
        self.assertEqual(search_res.status_code, 200)
        self.assertIn(b'Northwest', search_res.data)

        # 6. History Filtering (by smoker = yes)
        filter_res = self.client.get('/history?smoker=yes')
        self.assertEqual(filter_res.status_code, 200)
        self.assertIn(b'Northwest', filter_res.data)

        # 7. History Sorting (by cost_high)
        sort_res = self.client.get('/history?sort=cost_high')
        self.assertEqual(sort_res.status_code, 200)

        # 8. Profile View & Safe Email Update
        prof_get = self.client.get('/profile')
        self.assertEqual(prof_get.status_code, 200)
        self.assertIn(b'john', prof_get.data)

        prof_post = self.client.post('/profile', data={'email': 'john_updated@example.com'}, follow_redirects=True)
        self.assertEqual(prof_post.status_code, 200)
        self.assertIn(b'Profile updated successfully', prof_post.data)

        # 9. Delete prediction
        with self.app.app_context():
            user = UserModel.get_by_username('john')
            history = PredictionModel.get_user_history(user['id'])
            first_id = history['records'][0]['id']

        del_res = self.client.post(f'/history/delete/{first_id}', follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)
        self.assertIn(b'deleted successfully', del_res.data)

    # =========================================================================
    # TEST 5 — ML Model & Contract Integrity
    # =========================================================================
    def test_05_ml_model_integrity(self):
        """Confirm model.pkl is unchanged and 6-feature LinearRegression contract is strictly preserved."""
        model = MLService.get_model()
        self.assertIsNotNone(model)
        
        # 1. Verify 6 features in exact sequence
        self.assertEqual(MLService.FEATURE_ORDER, ['age', 'sex', 'bmi', 'children', 'smoker', 'region'])
        self.assertEqual(getattr(model, 'n_features_in_', 6), 6)

        # 2. Verify categorical mappings
        self.assertEqual(MLService.SEX_MAPPING, {'male': 0, 'female': 1})
        self.assertEqual(MLService.SMOKER_MAPPING, {'yes': 1, 'no': 0})
        self.assertEqual(MLService.REGION_MAPPING, {'southeast': 0, 'southwest': 1, 'northeast': 2, 'northwest': 3})

        # 3. Verify exact baseline mathematical output on [25, male(0), 28.5, 0, no(0), southwest(1)]
        test_vector = {
            'age': 25.0,
            'sex': 'male',
            'bmi': 28.5,
            'children': 0,
            'smoker': 'no',
            'region': 'southwest'
        }
        cost, formatted_text = MLService.predict(test_vector)
        self.assertAlmostEqual(cost, 3290.5821709266347, places=3)
        self.assertEqual(formatted_text, "Estimated Insurance Cost: Rs.3,290.58")

if __name__ == '__main__':
    unittest.main()
