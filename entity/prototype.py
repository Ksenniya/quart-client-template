import asyncio
import uuid
import time
import base64
from datetime import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify, Response
import aiohttp
from quart_schema import QuartSchema, validate_request, validate_querystring

app = Quart(__name__)
QuartSchema(app)

# Data Schemas for validation

@dataclass
class CreateUserSchema:
    username: str
    email: str
    password: str

@dataclass
class LoginUserSchema:
    email: str
    password: str

@dataclass
class CreatePostSchema:
    title: str
    user_id: str  # Expecting user_id from client
    topics: list
    body: str
    images: list = None

@dataclass
class VotePayload:
    user_id: str
    vote: str  # "up" or "down"

@dataclass
class AddCommentSchema:
    user_id: str
    body: str

@dataclass
class UploadImageSchema:
    user_id: str
    image_data: str  # base64 encoded string
    metadata: dict

@dataclass
class PaginationSchema:
    limit: int = 20
    offset: int = 0

# In-memory "databases" (mocks for prototype)
USERS = {}
POSTS = {}
COMMENTS = {}  # Key: post_id, Value: list of comments
IMAGES = {}    # Key: post_id, Value: dict of image_id to image data

# For processing tasks (mock job queue)
entity_jobs = {}

# Helper function to simulate external API call
async def external_api_call(data):
    async with aiohttp.ClientSession() as session:
        # TODO: Replace with real external API endpoint and business logic if available.
        async with session.post("http://example.com/external", json=data) as resp:
            # For prototype, we simply mock a response
            return await resp.json() if resp.status == 200 else {"result": "default"}

# Async processing task (Fire and forget pattern)
async def process_entity(job_data, post_data):
    # TODO: Implement the actual business logic and processing here.
    await asyncio.sleep(1)  # Simulate processing delay
    job_data["status"] = "completed"
    # For instance, you might update the POST record after processing external data.
    POSTS[post_data["post_id"]]["processedAt"] = datetime.utcnow().isoformat()

# 1. User Authentication

@app.route('/users/create', methods=['POST'])
@validate_request(CreateUserSchema)  # TODO: Validation decorator placed after route decorator for POST (workaround for quart-schema issue)
async def create_user(data: CreateUserSchema):
    user_id = str(uuid.uuid4())
    USERS[user_id] = {
        "username": data.username,
        "email": data.email,
        "password": data.password  # TODO: Do not store plain passwords in production.
    }
    return jsonify({
        "user_id": user_id,
        "username": data.username,
        "email": data.email,
        "message": "User created successfully."
    })

@app.route('/users/login', methods=['POST'])
@validate_request(LoginUserSchema)  # POST validation decorator placed after route decorator
async def login_user(data: LoginUserSchema):
    for user_id, user in USERS.items():
        if user["email"] == data.email and user["password"] == data.password:
            # TODO: Generate a real JWT token.
            token = f"token-{user_id}"
            return jsonify({
                "user_id": user_id,
                "token": token,
                "message": "Login successful."
            })
    return jsonify({"message": "Invalid credentials"}), 401

# 2. Post Management

@app.route('/posts', methods=['POST'])
@validate_request(CreatePostSchema)  # POST validation decorator placed after route decorator
async def create_post(data: CreatePostSchema):
    post_id = str(uuid.uuid4())
    POSTS[post_id] = {
        "post_id": post_id,
        "title": data.title,
        "user_id": data.user_id,
        "topics": data.topics,
        "upvotes": 0,
        "downvotes": 0,
        "body": data.body,
        "images": data.images if data.images is not None else [],
        "createdAt": datetime.utcnow().isoformat()
    }
    # Simulate external business logic processing
    job_id = str(uuid.uuid4())
    requested_at = time.time()
    entity_jobs[job_id] = {"status": "processing", "requestedAt": requested_at}
    # Fire and forget the processing task.
    asyncio.create_task(process_entity(entity_jobs[job_id], POSTS[post_id]))
    return jsonify({**POSTS[post_id], "message": "Post created successfully."})

@validate_querystring(PaginationSchema)  # GET validation decorator placed before route decorator for GET requests (workaround for quart-schema issue)
@app.route('/posts', methods=['GET'])
async def get_posts():
    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))
    all_posts = list(POSTS.values())
    paginated = all_posts[offset:offset + limit]
    return jsonify({
        "posts": paginated,
        "limit": limit,
        "offset": offset,
        "total": len(all_posts)
    })

@app.route('/posts/<post_id>', methods=['GET'])
async def get_post(post_id):
    post = POSTS.get(post_id)
    if post:
        return jsonify(post)
    return jsonify({"message": "Post not found"}), 404

@app.route('/posts/<post_id>', methods=['DELETE'])
async def delete_post(post_id):
    # TODO: Validate that the requesting user is the owner of the post.
    if post_id in POSTS:
        del POSTS[post_id]
        return jsonify({"post_id": post_id, "message": "Post deleted successfully."})
    return jsonify({"message": "Post not found"}), 404

@app.route('/posts/<post_id>/vote', methods=['POST'])
@validate_request(VotePayload)  # POST validation decorator placed after route decorator
async def vote_post(data: VotePayload, post_id):
    post = POSTS.get(post_id)
    if not post:
        return jsonify({"message": "Post not found"}), 404

    if data.vote == "up":
        post["upvotes"] += 1
    elif data.vote == "down":
        post["downvotes"] += 1
    else:
        return jsonify({"message": "Invalid vote value"}), 400

    return jsonify({
        "post_id": post_id,
        "upvotes": post["upvotes"],
        "downvotes": post["downvotes"],
        "message": "Vote recorded."
    })

# 3. Comment Management

@app.route('/posts/<post_id>/comments', methods=['POST'])
@validate_request(AddCommentSchema)  # POST validation decorator placed after route decorator
async def add_comment(data: AddCommentSchema, post_id):
    if post_id not in POSTS:
        return jsonify({"message": "Post not found"}), 404

    comment_id = str(uuid.uuid4())
    comment = {
        "comment_id": comment_id,
        "post_id": post_id,
        "user_id": data.user_id,
        "body": data.body,
        "upvotes": 0,
        "downvotes": 0,
        "createdAt": datetime.utcnow().isoformat()
    }
    COMMENTS.setdefault(post_id, []).append(comment)
    return jsonify({**comment, "message": "Comment added successfully."})

@validate_querystring(PaginationSchema)  # GET validation decorator placed before route decorator for GET requests
@app.route('/posts/<post_id>/comments', methods=['GET'])
async def get_comments(post_id):
    if post_id not in POSTS:
        return jsonify({"message": "Post not found"}), 404

    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))
    post_comments = COMMENTS.get(post_id, [])
    paginated = post_comments[offset: offset + limit]
    return jsonify({
        "post_id": post_id,
        "comments": paginated,
        "limit": limit,
        "offset": offset,
        "total": len(post_comments)
    })

@app.route('/posts/<post_id>/comments/<comment_id>', methods=['DELETE'])
async def delete_comment(post_id, comment_id):
    if post_id not in COMMENTS:
        return jsonify({"message": "Post or comment not found"}), 404

    # TODO: Validate that the requesting user is the owner of the comment.
    updated_comments = [c for c in COMMENTS[post_id] if c["comment_id"] != comment_id]
    COMMENTS[post_id] = updated_comments
    return jsonify({"comment_id": comment_id, "message": "Comment deleted successfully."})

@app.route('/posts/<post_id>/comments/<comment_id>/vote', methods=['POST'])
@validate_request(VotePayload)  # POST validation decorator placed after route decorator
async def vote_comment(data: VotePayload, post_id, comment_id):
    if post_id not in COMMENTS:
        return jsonify({"message": "Post or comment not found"}), 404

    for comment in COMMENTS[post_id]:
        if comment["comment_id"] == comment_id:
            if data.vote == "up":
                comment["upvotes"] += 1
            elif data.vote == "down":
                comment["downvotes"] += 1
            else:
                return jsonify({"message": "Invalid vote value"}), 400
            return jsonify({
                "comment_id": comment_id,
                "upvotes": comment["upvotes"],
                "downvotes": comment["downvotes"],
                "message": "Vote recorded."
            })
    return jsonify({"message": "Comment not found"}), 404

# 4. Image Management

@app.route('/posts/<post_id>/images', methods=['POST'])
@validate_request(UploadImageSchema)  # POST validation decorator placed after route decorator
async def upload_image(data: UploadImageSchema, post_id):
    if post_id not in POSTS:
        return jsonify({"message": "Post not found"}), 404

    image_id = str(uuid.uuid4())
    # For prototype, we store the base64 encoded image data along with metadata.
    image_data = {
        "user_id": data.user_id,
        "image_data": data.image_data,  # base64 encoded
        "metadata": data.metadata,
        "uploadedAt": datetime.utcnow().isoformat()
    }
    IMAGES.setdefault(post_id, {})[image_id] = image_data
    return jsonify({
        "image_id": image_id,
        "message": "Image uploaded successfully."
    })

@app.route('/posts/<post_id>/images/<image_id>', methods=['GET'])
async def retrieve_image(post_id, image_id):
    if post_id not in IMAGES or image_id not in IMAGES[post_id]:
        return jsonify({"message": "Image not found"}), 404

    image_record = IMAGES[post_id][image_id]
    # Decode the base64 image data and serve the raw image bytes.
    image_bytes = base64.b64decode(image_record["image_data"])
    content_type = image_record["metadata"].get("content_type", "application/octet-stream")
    return Response(image_bytes, mimetype=content_type)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)