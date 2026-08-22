import unittest
import os
import tempfile
from app import create_app
from config import Config
from database import init_db, get_db

class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key-12345'

class TestApplicationEndToEnd(unittest.TestCase):
    """
    Comprehensive End-to-End integration test covering:
    - User Registration (including duplicate checks)
    - Authentication (Login/Logout)
    - Protected Route Access Control
    - ML Prediction execution & persistence
    - Prediction History & User Isolation
    - History Deletion
    - Stale Session / Foreign Key Protection
    """

    def setUp(self):
        # Create a dedicated temp database for isolated test runs
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        TestConfig.DATABASE_PATH = self.db_path

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

    def test_user_registration_and_duplicate_check(self):
        """Test registration flow and rejection of duplicate username."""
        # Valid registration
        res = self.client.post('/register', data={
            'username': 'alice',
            'email': 'alice@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Registration successful', res.data)

        # Duplicate username attempt
        res_dup = self.client.post('/register', data={
            'username': 'alice',
            'email': 'alice2@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertIn(b'already taken', res_dup.data)

    def test_login_and_logout(self):
        """Test authentication, session establishment, and logout."""
        # Register user
        self.client.post('/register', data={
            'username': 'bob',
            'password': 'secretpassword',
            'confirm_password': 'secretpassword'
        })

        # Login with wrong password
        res_fail = self.client.post('/login', data={
            'username': 'bob',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertIn(b'Invalid username or password', res_fail.data)

        # Login with correct password
        res_success = self.client.post('/login', data={
            'username': 'bob',
            'password': 'secretpassword'
        }, follow_redirects=True)
        self.assertEqual(res_success.status_code, 200)
        self.assertIn(b'Welcome back', res_success.data)

        # Logout
        res_logout = self.client.get('/logout', follow_redirects=True)
        self.assertIn(b'logged out successfully', res_logout.data)

    def test_protected_routes(self):
        """Verify unauthenticated users cannot access protected views."""
        protected_endpoints = ['/dashboard', '/predict-form', '/predict', '/history', '/profile']
        for endpoint in protected_endpoints:
            res = self.client.get(endpoint, follow_redirects=False)
            # Expect redirect (302) to login page
            self.assertEqual(res.status_code, 302, f"Endpoint {endpoint} was not protected!")
            self.assertIn('/login', res.headers.get('Location', ''))

    def test_stale_session_foreign_key_protection(self):
        """Verify that a session with an orphaned/non-existent user_id is gracefully redirected without crashing."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 99999  # User ID not in database
            sess['username'] = 'ghost_user'

        # Attempt to access predict form
        res_form = self.client.get('/predict-form', follow_redirects=True)
        self.assertEqual(res_form.status_code, 200)
        self.assertIn(b'session is invalid', res_form.data)

        # Attempt to submit a prediction with stale session
        with self.client.session_transaction() as sess:
            sess['user_id'] = 99999
            sess['username'] = 'ghost_user'

        res_post = self.client.post('/predict', data={
            'age': '30',
            'sex': 'male',
            'bmi': '25.0',
            'children': '0',
            'smoker': 'no',
            'region': 'southwest'
        }, follow_redirects=True)
        self.assertEqual(res_post.status_code, 200)
        self.assertIn(b'session is invalid', res_post.data)

    def test_prediction_workflow_and_persistence(self):
        """Test full prediction submission, result calculation, and history listing."""
        # 1. Register and login
        self.client.post('/register', data={
            'username': 'charlie',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        self.client.post('/login', data={
            'username': 'charlie',
            'password': 'password123'
        })

        # 2. Submit valid prediction
        pred_res = self.client.post('/predict', data={
            'age': '35',
            'sex': 'female',
            'bmi': '24.5',
            'children': '1',
            'smoker': 'no',
            'region': 'northwest'
        }, follow_redirects=True)

        self.assertEqual(pred_res.status_code, 200)
        self.assertIn(b'Prediction Result', pred_res.data)
        self.assertIn(b'Input Features Summary', pred_res.data)

        # 3. Check history page
        hist_res = self.client.get('/history')
        self.assertEqual(hist_res.status_code, 200)
        self.assertIn(b'Northwest', hist_res.data)
        self.assertIn(b'Non-Smoker', hist_res.data)

    def test_user_history_isolation(self):
        """Ensure User B cannot see or delete User A's predictions."""
        # Setup User A
        self.client.post('/register', data={'username': 'usera', 'password': 'password123', 'confirm_password': 'password123'})
        self.client.post('/login', data={'username': 'usera', 'password': 'password123'})
        
        # User A makes prediction (age=55)
        self.client.post('/predict', data={
            'age': '55',
            'sex': 'male',
            'bmi': '30.0',
            'children': '2',
            'smoker': 'yes',
            'region': 'southeast'
        }, follow_redirects=True)
        self.client.get('/logout')

        # Setup User B
        self.client.post('/register', data={'username': 'userb', 'password': 'password123', 'confirm_password': 'password123'})
        self.client.post('/login', data={'username': 'userb', 'password': 'password123'})

        # User B views history
        hist_res = self.client.get('/history')
        # User B should NOT see User A's age=55 / smoker=yes record
        self.assertNotIn(b'55</td>', hist_res.data)
        self.assertIn(b'No prediction records match', hist_res.data)

        # Attempt to access or delete User A's prediction directly via ID 1
        del_res = self.client.post('/history/delete/1', follow_redirects=True)
        self.assertIn(b'Failed to delete', del_res.data)

if __name__ == '__main__':
    unittest.main()
