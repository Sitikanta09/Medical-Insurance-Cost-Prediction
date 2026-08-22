from database import get_db
import sqlite3

class PredictionModel:
    """Encapsulates persistent database operations for ML Predictions."""

    @staticmethod
    def create(user_id, age, sex, bmi, children, smoker, region, predicted_cost):
        """
        Record a newly generated prediction for a user.
        Ensures foreign key constraints are met.
        Returns the inserted prediction dictionary.
        """
        db = get_db()
        try:
            cursor = db.execute(
                """
                INSERT INTO predictions (user_id, age, sex, bmi, children, smoker, region, predicted_cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (int(user_id), float(age), str(sex), float(bmi), int(children), str(smoker), str(region), float(predicted_cost))
            )
            db.commit()
            return PredictionModel.get_by_id(cursor.lastrowid, user_id)
        except sqlite3.IntegrityError as e:
            db.rollback()
            if "foreign key" in str(e).lower():
                raise ValueError(f"Cannot save prediction: User ID {user_id} does not exist in the database.") from e
            raise

    @staticmethod
    def get_by_id(prediction_id, user_id):
        """
        Retrieve a specific prediction ensuring it belongs to the requesting user.
        Prevents unauthorized cross-user data access.
        """
        db = get_db()
        row = db.execute(
            "SELECT * FROM predictions WHERE id = ? AND user_id = ?",
            (prediction_id, user_id)
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_user_history(user_id, search="", region_filter=None, smoker_filter=None, sort_by="newest", page=1, per_page=10):
        """
        Retrieve paginated, filterable, and searchable prediction history for a user.
        """
        db = get_db()
        query = "SELECT * FROM predictions WHERE user_id = ?"
        params = [user_id]

        # Search by age or region or smoker
        if search:
            query += " AND (region LIKE ? OR smoker LIKE ? OR CAST(age AS TEXT) LIKE ?)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])

        if region_filter and region_filter in ['southeast', 'southwest', 'northeast', 'northwest']:
            query += " AND region = ?"
            params.append(region_filter)

        if smoker_filter and smoker_filter in ['yes', 'no']:
            query += " AND smoker = ?"
            params.append(smoker_filter)

        # Count total matching rows
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        total_count = db.execute(count_query, params).fetchone()[0]

        # Sort order
        if sort_by == "oldest":
            query += " ORDER BY created_at ASC, id ASC"
        elif sort_by == "cost_high":
            query += " ORDER BY predicted_cost DESC"
        elif sort_by == "cost_low":
            query += " ORDER BY predicted_cost ASC"
        else:  # newest default
            query += " ORDER BY created_at DESC, id DESC"

        # Pagination
        offset = (page - 1) * per_page
        query += " LIMIT ? OFFSET ?"
        params.extend([per_page, offset])

        rows = db.execute(query, params).fetchall()
        records = [dict(row) for row in rows]
        total_pages = max(1, (total_count + per_page - 1) // per_page)

        return {
            'records': records,
            'total_count': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages
        }

    @staticmethod
    def get_user_stats(user_id):
        """Aggregate statistical metrics for the user dashboard."""
        db = get_db()
        stats_row = db.execute(
            """
            SELECT 
                COUNT(*) as total_predictions,
                AVG(predicted_cost) as avg_cost,
                MIN(predicted_cost) as min_cost,
                MAX(predicted_cost) as max_cost
            FROM predictions 
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        latest_row = db.execute(
            "SELECT predicted_cost, created_at FROM predictions WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT 1",
            (user_id,)
        ).fetchone()

        return {
            'total_predictions': stats_row['total_predictions'] if stats_row else 0,
            'avg_cost': round(stats_row['avg_cost'], 2) if (stats_row and stats_row['avg_cost'] is not None) else 0.0,
            'min_cost': round(stats_row['min_cost'], 2) if (stats_row and stats_row['min_cost'] is not None) else 0.0,
            'max_cost': round(stats_row['max_cost'], 2) if (stats_row and stats_row['max_cost'] is not None) else 0.0,
            'latest_cost': round(latest_row['predicted_cost'], 2) if latest_row else None,
            'latest_date': latest_row['created_at'] if latest_row else None
        }

    @staticmethod
    def get_recent(user_id, limit=5):
        """Retrieve recent predictions for dashboard display."""
        db = get_db()
        rows = db.execute(
            "SELECT * FROM predictions WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def delete(prediction_id, user_id):
        """Delete a prediction belonging strictly to user_id."""
        db = get_db()
        cursor = db.execute(
            "DELETE FROM predictions WHERE id = ? AND user_id = ?",
            (prediction_id, user_id)
        )
        db.commit()
        return cursor.rowcount > 0
