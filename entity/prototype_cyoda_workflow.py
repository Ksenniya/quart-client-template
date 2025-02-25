#!/usr/bin/env python3
import asyncio
import uuid
import time
import base64
from datetime import datetime
from dataclasses import dataclass
from quart import Quart, request, jsonify, Response
import aiohttp
from quart_schema import QuartSchema, validate_request, validate_querystring

# Import external entity service functions and required constants
from app_init.app_init import entity_service, cyoda_token
from common.config.config import ENTITY_VERSION
from common.repository.cyoda.cyoda_init import init_cyoda

app = Quart(__name__)
QuartSchema(app)

# Workflow functions applied to entities before persistence
async def process_user(entity):
    # Add creation timestamp if not already present
    if "createdAt" not in entity:
        entity["createdAt"] = datetime.utcnow().isoformat()
    # Additional processing logic for users can be added here
    return entity

async def process_post(entity):
    # Mark the post as newly processed by the workflow function
    entity["workflow_processed"] = True
    # Additional processing logic for posts can be added here
    return entity

async def process_comment(entity):
    # Add creation timestamp for comment if not already present
    if "createdAt" not in entity:
        entity["createdAt"] = datetime.utcnow().isoformat()
    # Additional processing logic for comments can be added here
    return entity

async def process_image(entity):
    # Add upload timestamp for image if not already present
    if "uploadedAt" not in entity:
        entity["uploadedAt"] = datetime.utcnow().isoformat()
    # Additional processing logic for images can be added here
    return entity

# Helper function to simulate external API call for demonstration purposes
async def external_api_call(data):
    async with aiohttp.ClientSession() as session:
        async with session.post("http://example.com/external", json=data) as resp:
            return await resp.json() if resp.status == 200 else {"result": "default"}

# Async processing task (Fire and forget pattern) for additional post processing
async def process_entity(job_data, post_id):
    # Simulate processing delay
    await asyncio.sleep(1)
    post = await entity_service.get_item(
        token=cyoda_token,
        entity_model="post",
        entity_version=ENTITY_VERSION,
        technical_id=post_id
    )
    if post:
        post["processedAt"] = datetime.utcnow().isoformat()
        await entity_service.update_item(
            token=cyoda_token,
            entity_model="post",
            entity_version=ENTITY_VERSION,
            entity=post,
            meta={}
        )
    # Optionally, update job status if required

# Startup initialization
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

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

# 1. User Authentication

@app.route('/users/create', methods=['POST'])
@validate_request(CreateUserSchema)
async def create_user(data: CreateUserSchema):
    # Prepare user data for external storage
    new_user = {
        "username": data.username,
        "email": data.email,
        "password": data.password  # Reminder: Do not store plain passwords in production.
    }
    user_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="user",
        entity_version=ENTITY_VERSION,
        entity=new_user,
        workflow=process_user  # Workflow function applied before persistence
    )
    # Return only the generated user id as per instructions
    return jsonify({
        "user_id": user_id,
        "message": "User created successfully."
    })

@app.route('/users/login', methods=['POST'])
@validate_request(LoginUserSchema)
async def login_user(data: LoginUserSchema):
    # Use condition-based retrieval from external service to find matching user
    condition = {"email": data.email, "password": data.password}
    users = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="user",
        entity_version=ENTITY_VERSION,
        condition=condition
    )
    if users and len(users) > 0:
        user = users[0]
        user_id = user.get("user_id", "unknown")
        # For demonstration, generate a dummy JWT token
        token = f"token-{user_id}"
        return jsonify({
            "user_id": user_id,
            "token": token,
            "message": "Login successful."
        })
    return jsonify({"message": "Invalid credentials"}), 401

# 2. Post Management

@app.route('/posts', methods=['POST'])
@validate_request(CreatePostSchema)
async def create_post(data: CreatePostSchema):
    post_id = str(uuid.uuid4())
    post_data = {
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
    new_post_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="post",
        entity_version=ENTITY_VERSION,
        entity=post_data,
        workflow=process_post  # Workflow function applied before persistence
    )
    # Simulate external business logic processing by launching a background task
    job_data = {"status": "processing", "requestedAt": time.time()}
    asyncio.create_task(process_entity(job_data, post_id))
    return jsonify({
        "post_id": new_post_id,
        "message": "Post created successfully."
    })

@app.route('/posts', methods=['GET'])
@validate_querystring(PaginationSchema)
async def get_posts():
    posts = await entity_service.get_items(
        token=cyoda_token,
        entity_model="post",
        entity_version=ENTITY_VERSION
    )
    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))
    total = len(posts) if posts else 0
    paginated = posts[offset: offset + limit] if posts else []
    return jsonify({
        "posts": paginated,
        "limit": limit,
        "offset": offset,
        "total": total
    })

@app.route('/posts/<post_id>', methods=['GET'])
async def get_post(post_id):
    post = await entity_service.get_item(
        token=cyoda_token,
        entity_model="post",
        entity_version=ENTITY_VERSION,
        technical_id=post_id
    )
    if post:
        return jsonify(post)
    return jsonify({"message": "Post not found"}), 404

@app.route('/posts/<post_id>', methods=['DELETE'])
async def delete_post(post_id):
    await entity_service.delete_item(
        token=cyoda_token,
        entity_model="post",
        entity_version=ENTITY_VERSION,
        entity={"post_id": post_id},
        meta={}
    )
    return jsonify({"post_id": post_id, "message": "Post deleted successfully."})

@app.route('/posts/<post_id>/vote', methods=['POST'])
@validate_request(VotePayload)
async def vote_post(data: VotePayload, post_id):
    post = await entity_service.get_item(
        token=cyoda_token,
        entity_model="post",
        entity_version=ENTITY_VERSION,
        technical_id=post_id
    )
    if not post:
        return jsonify({"message": "Post not found"}), 404

    if data.vote == "up":
        post["upvotes"] = post.get("upvotes", 0) + 1
    elif data.vote == "down":
        post["downvotes"] = post.get("downvotes", 0) + 1
    else:
        return jsonify({"message": "Invalid vote value"}), 400

    await entity_service.update_item(
        token=cyoda_token,
        entity_model="post",
        entity_version=ENTITY_VERSION,
        entity=post,
        meta={}
    )
    return jsonify({
        "post_id": post_id,
        "upvotes": post.get("upvotes"),
        "downvotes": post.get("downvotes"),
        "message": "Vote recorded."
    })

# 3. Comment Management

@app.route('/posts/<post_id>/comments', methods=['POST'])
@validate_request(AddCommentSchema)
async def add_comment(data: AddCommentSchema, post_id):
    # Check if the post exists
    post = await entity_service.get_item(
        token=cyoda_token,
        entity_model="post",
        entity_version=ENTITY_VERSION,
        technical_id=post_id
    )
    if not post:
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
    new_comment_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="comment",
        entity_version=ENTITY_VERSION,
        entity=comment,
        workflow=process_comment  # Workflow function applied before persistence
    )
    return jsonify({
        "comment_id": new_comment_id,
        "message": "Comment added successfully."
    })

@app.route('/posts/<post_id>/comments', methods=['GET'])
@validate_querystring(PaginationSchema)
async def get_comments(post_id):
    # Validate post existence
    post = await entity_service.get_item(
        token=cyoda_token,
        entity_model="post",
        entity_version=ENTITY_VERSION,
        technical_id=post_id
    )
    if not post:
        return jsonify({"message": "Post not found"}), 404

    limit = int(request.args.get("limit", 20))
    offset = int(request.args.get("offset", 0))
    comments = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="comment",
        entity_version=ENTITY_VERSION,
        condition={"post_id": post_id}
    )
    total = len(comments) if comments else 0
    paginated = comments[offset: offset + limit] if comments else []
    return jsonify({
        "post_id": post_id,
        "comments": paginated,
        "limit": limit,
        "offset": offset,
        "total": total
    })

@app.route('/posts/<post_id>/comments/<comment_id>', methods=['DELETE'])
async def delete_comment(post_id, comment_id):
    await entity_service.delete_item(
        token=cyoda_token,
        entity_model="comment",
        entity_version=ENTITY_VERSION,
        entity={"comment_id": comment_id, "post_id": post_id},
        meta={}
    )
    return jsonify({"comment_id": comment_id, "message": "Comment deleted successfully."})

@app.route('/posts/<post_id>/comments/<comment_id>/vote', methods=['POST'])
@validate_request(VotePayload)
async def vote_comment(data: VotePayload, post_id, comment_id):
    comment = await entity_service.get_item(
        token=cyoda_token,
        entity_model="comment",
        entity_version=ENTITY_VERSION,
        technical_id=comment_id
    )
    if not comment:
        return jsonify({"message": "Comment not found"}), 404

    if data.vote == "up":
        comment["upvotes"] = comment.get("upvotes", 0) + 1
    elif data.vote == "down":
        comment["downvotes"] = comment.get("downvotes", 0) + 1
    else:
        return jsonify({"message": "Invalid vote value"}), 400

    await entity_service.update_item(
        token=cyoda_token,
        entity_model="comment",
        entity_version=ENTITY_VERSION,
        entity=comment,
        meta={}
    )
    return jsonify({
        "comment_id": comment_id,
        "upvotes": comment.get("upvotes"),
        "downvotes": comment.get("downvotes"),
        "message": "Vote recorded."
    })

# 4. Image Management

@app.route('/posts/<post_id>/images', methods=['POST'])
@validate_request(UploadImageSchema)
async def upload_image(data: UploadImageSchema, post_id):
    # Check if post exists
    post = await entity_service.get_item(
        token=cyoda_token,
        entity_model="post",
        entity_version=ENTITY_VERSION,
        technical_id=post_id
    )
    if not post:
        return jsonify({"message": "Post not found"}), 404

    image_id = str(uuid.uuid4())
    image_data = {
        "image_id": image_id,
        "post_id": post_id,
        "user_id": data.user_id,
        "image_data": data.image_data,  # base64 encoded string
        "metadata": data.metadata,
        "uploadedAt": datetime.utcnow().isoformat()
    }
    new_image_id = await entity_service.add_item(
        token=cyoda_token,
        entity_model="image",
        entity_version=ENTITY_VERSION,
        entity=image_data,
        workflow=process_image  # Workflow function applied before persistence
    )
    return jsonify({
        "image_id": new_image_id,
        "message": "Image uploaded successfully."
    })

@app.route('/posts/<post_id>/images/<image_id>', methods=['GET'])
async def retrieve_image(post_id, image_id):
    image_record = await entity_service.get_item(
        token=cyoda_token,
        entity_model="image",
        entity_version=ENTITY_VERSION,
        technical_id=image_id
    )
    if not image_record or image_record.get("post_id") != post_id:
        return jsonify({"message": "Image not found"}), 404

    image_bytes = base64.b64decode(image_record.get("image_data"))
    content_type = image_record.get("metadata", {}).get("content_type", "application/octet-stream")
    return Response(image_bytes, mimetype=content_type)

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)