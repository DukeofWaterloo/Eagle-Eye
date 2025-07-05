import psycopg2
from config import Config
import hashlib
from passlib.hash import pbkdf2_sha256

class DBService:
    def __init__(self):
        self.conn = psycopg2.connect(Config.SQLALCHEMY_DATABASE_URI)
    
    def save_business(self, name, gmb_id, phone, email, tone='professional', business_id=None):
        try:
            with self.conn.cursor() as cur:
                if business_id:
                    cur.execute("""
                        UPDATE businesses SET name=%s, gmb_account_id=%s, owner_phone=%s, owner_email=%s, response_tone=%s WHERE id=%s
                    """, (name, gmb_id, phone, email, tone, business_id))
                else:
                    cur.execute("""
                        INSERT INTO businesses (name, gmb_account_id, owner_phone, owner_email, response_tone)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                    """, (name, gmb_id, phone, email, tone))
                    business_id = cur.fetchone()[0]
            self.conn.commit()
            return business_id
        except Exception as e:
            self.conn.rollback()
            raise e
    
    def save_review(self, business_id, review_text, rating, source='google'):
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO reviews (business_id, review_text, rating, source, created_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'America/Toronto')
                    RETURNING id
                """, (business_id, review_text, rating, source))
                review_id = cur.fetchone()[0]
            self.conn.commit()
            return review_id
        except Exception as e:
            self.conn.rollback()
            raise e
    
    def save_ai_responses(self, review_id, responses):
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO ai_responses (review_id, option1, option2, option3)
                    VALUES (%s, %s, %s, %s)
                """, (review_id, responses[0], responses[1], responses[2]))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e
    
    def get_pending_reviews(self, business_id=None, status='pending', search=None, start_date=None, end_date=None, limit=10, offset=0):
        query = '''
            SELECT r.id, r.review_text, r.rating, r.created_at, b.name 
            FROM reviews r
            JOIN businesses b ON r.business_id = b.id
            WHERE 1=1
        '''
        params = []
        if business_id:
            query += ' AND b.id = %s'
            params.append(business_id)
        if status:
            query += ' AND r.response_status = %s'
            params.append(status)
        if search:
            query += ' AND r.review_text ILIKE %s'
            params.append(f'%{search}%')
        if start_date:
            query += ' AND r.created_at >= %s'
            params.append(start_date)
        if end_date:
            query += ' AND r.created_at <= %s'
            params.append(end_date)
        query += ' ORDER BY r.created_at DESC LIMIT %s OFFSET %s'
        params.extend([limit, offset])
        with self.conn.cursor() as cur:
            cur.execute(query, tuple(params))
            return cur.fetchall()
    
    def get_review_details(self, review_id):
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT r.id, r.review_text, r.rating, r.created_at, r.source, 
                       b.name, b.id as business_id, ar.option1, ar.option2, ar.option3
                FROM reviews r
                JOIN businesses b ON r.business_id = b.id
                LEFT JOIN ai_responses ar ON r.id = ar.review_id
                WHERE r.id = %s
            """, (review_id,))
            return cur.fetchone()
    
    def save_response(self, review_id, response_text):
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE reviews 
                    SET response_status = 'responded', 
                        response_text = %s,
                        responded_at = CURRENT_TIMESTAMP AT TIME ZONE 'America/Toronto'
                    WHERE id = %s
                """, (response_text, review_id))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e

    def create_user(self, username, password):
        password_hash = pbkdf2_sha256.hash(password)
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (username, password_hash)
                    VALUES (%s, %s)
                    RETURNING id
                """, (username, password_hash))
                user_id = cur.fetchone()[0]
            self.conn.commit()
            return user_id
        except Exception as e:
            self.conn.rollback()
            raise e

    def get_user_by_username(self, username):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, username, password_hash FROM users WHERE username = %s", (username,))
            user = cur.fetchone()
            if user is None:
                return None
            return user

    def verify_user(self, username, password):
        user = self.get_user_by_username(username)
        if user is not None and pbkdf2_sha256.verify(password, user[2]):
            return user
        return None

    def get_user_by_id(self, user_id):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, username, password_hash FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            if user is None:
                return None
            return user

    def get_all_businesses(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, name FROM businesses ORDER BY name ASC")
            return cur.fetchall()

    def get_business_by_id(self, business_id):
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, name, gmb_account_id, owner_phone, owner_email, response_tone FROM businesses WHERE id = %s", (business_id,))
            return cur.fetchone()

    def save_response_feedback(self, review_id, rating):
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO response_feedback (review_id, rating)
                    VALUES (%s, %s)
                    ON CONFLICT (review_id) DO UPDATE SET rating = EXCLUDED.rating
                """, (review_id, rating))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e

    def get_response_feedback(self, review_id):
        with self.conn.cursor() as cur:
            cur.execute("SELECT rating FROM response_feedback WHERE review_id = %s", (review_id,))
            result = cur.fetchone()
            return result[0] if result else None
