import os
from flask import Flask, request, session, jsonify, make_response
from flask_restful import Api, Resource
from flask_migrate import Migrate
from models import db, bcrypt, User, Note

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SESSION_SECRET_KEY', 'super_secret_productivity_key')

db.init_app(app)
bcrypt.init_app(app)
migrate = Migrate(app, db)
api = Api(app)


# --- Authentication Views ---

class Signup(Resource):
    def post(self):
        data = request.get_json()
        if not data or not data.get('username') or not data.get('password'):
            return {"error": "Username and password are required"}, 400

        if User.query.filter_by(username=data.get('username')).first():
            return {"error": "Username already taken"}, 422

        try:
            new_user = User(username=data.get('username'))
            new_user.password_hash = data.get('password')
            db.session.add(new_user)
            db.session.commit()

            session['user_id'] = new_user.id
            return {"id": new_user.id, "username": new_user.username}, 201
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500


class Login(Resource):
    def post(self):
        data = request.get_json()
        if not data:
            return {"error": "Invalid input"}, 400

        user = User.query.filter_by(username=data.get('username')).first()
        if user and user.authenticate(data.get('password')):
            session['user_id'] = user.id
            return {"id": user.id, "username": user.username}, 200

        return {"error": "Invalid username or password"}, 401


class CheckSession(Resource):
    def get(self):
        user_id = session.get('user_id')
        if user_id:
            user = User.query.get(user_id)
            if user:
                return {"id": user.id, "username": user.username}, 200
        return {"error": "Unauthorized"}, 401


class Logout(Resource):
    def delete(self):
        if 'user_id' in session:
            session.pop('user_id')
            return {}, 204
        return {"error": "Unauthorized"}, 401


# --- Note Resource Views (CRUD & Pagination & User Ownership) ---

class NoteListResource(Resource):
    def get(self):
        user_id = session.get('user_id')
        if not user_id:
            return {"error": "Unauthorized"}, 401

        # Pagination parameters (?page=1&per_page=5)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 5, type=int)

        # Restrict notes to only the currently logged-in user
        pagination = Note.query.filter_by(user_id=user_id).paginate(page=page, per_page=per_page, error_out=False)
        
        notes = [note.to_dict() for note in pagination.items]
        return {
            "notes": notes,
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": pagination.page
        }, 200

    def post(self):
        user_id = session.get('user_id')
        if not user_id:
            return {"error": "Unauthorized"}, 401

        data = request.get_json()
        if not data or not data.get('title') or not data.get('content'):
            return {"error": "Title and content are required"}, 400

        try:
            new_note = Note(
                title=data.get('title'),
                content=data.get('content'),
                user_id=user_id
            )
            db.session.add(new_note)
            db.session.commit()
            return new_note.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500


class NoteResource(Resource):
    def get(self, id):
        user_id = session.get('user_id')
        if not user_id:
            return {"error": "Unauthorized"}, 401

        note = Note.query.filter_by(id=id, user_id=user_id).first()
        if not note:
            return {"error": "Note not found or unauthorized"}, 404

        return note.to_dict(), 200

    def patch(self, id):
        user_id = session.get('user_id')
        if not user_id:
            return {"error": "Unauthorized"}, 401

        note = Note.query.filter_by(id=id, user_id=user_id).first()
        if not note:
            return {"error": "Note not found or unauthorized"}, 404

        data = request.get_json()
        if not data:
            return {"error": "No update data provided"}, 400

        try:
            if 'title' in data:
                note.title = data['title']
            if 'content' in data:
                note.content = data['content']

            db.session.commit()
            return note.to_dict(), 200
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500

    def delete(self, id):
        user_id = session.get('user_id')
        if not user_id:
            return {"error": "Unauthorized"}, 401

        note = Note.query.filter_by(id=id, user_id=user_id).first()
        if not note:
            return {"error": "Note not found or unauthorized"}, 404

        try:
            db.session.delete(note)
            db.session.commit()
            return {}, 204
        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 500


# Register API Routes
api.add_resource(Signup, '/signup')
api.add_resource(Login, '/login')
api.add_resource(CheckSession, '/check_session')
api.add_resource(Logout, '/logout')
api.add_resource(NoteListResource, '/notes')
api.add_resource(NoteResource, '/notes/<int:id>')

if __name__ == '__main__':
    app.run(port=5555, debug=True)