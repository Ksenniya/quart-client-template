Below is one valid refactoring of the code. Notice that all direct interactions with the local dictionaries (users, posts, etc.) have been replaced by calls to the external service via entity_service. In some cases—such as for login where a “by‐condition” lookup is needed—you see that we call get_items_by_condition. (If the provided entity_service functions were insufficient for some business logic, we “skip” that part as noted in the instructions.) Also, the startup code and imports have been added as required.

------------------------------------------------------------
#!/usr/bin/env python3
from dataclasses import dataclass
from uuid import uuid4

from quart import Quart, jsonify, request
from quart_schema import QuartSchema, validate_request

# NEW: Imports needed for external service initialization and token
from common.repository.cyoda.cyoda_init import init_cyoda
from app_init.app_init import cyoda_token, entity_service

app = Quart(__name__)
QuartSchema(app)

# The constant for entity version – assumed defined in scope.
ENTITY_VERSION = "1.0"

# Setup startup code for external integration with cyoda.
@app.before_serving
async def startup():
    await init_cyoda(cyoda_token)

# Data classes for request validation

@dataclass
class UserCreate:
    username: str
    password: str

@dataclass
class UserLogin:
    username: str
    password: str

@dataclass
class PostCreate:
    title: str
    # Although tags are a list, for simplicity we assume a comma‐separated string.
    # TODO: Improve tags handling later.
    tags: str  
    body: str
    # Remove user_id from request in real implementation; token should provide user info.
    user_id: str = ""  # optional placeholder

@dataclass
class CommentCreate:
    body: str
    user_id: str = ""  # TODO: Get user_id from token in production

@dataclass
class VoteRequest:
    vote: str   # Allowed values "up" or "down"

@dataclass
class ImageUpload:
    # TODO: In a real scenario, handle file uploads natively rather than a string.
    image: str


# NOTE: The in‐memory dictionaries are no longer used.
# We now rely on the external entity_service for persistence.

@app.route('/users', methods=['POST'])
@validate_request(UserCreate)
async def create_user(data: UserCreate):
    user_id = str(uuid4())
    # Prepare the entity record including the generated id.
    user_entity = {
        'user_id': user_id,
        'username': data.username,
        'password': data.password  # TODO: Hash the password in production
    }
    await entity_service.add_item(
        token=cyoda_token,
        entity_model="users",
        entity_version=ENTITY_VERSION,
        entity=user_entity
    )
    # Return a mocked JWT token along with the new user id.
    return jsonify({'token': 'JWT', 'user_id': user_id})


@app.route('/users/login', methods=['POST'])
@validate_request(UserLogin)
async def login_user(data: UserLogin):
    # Query the external service for users with the matching username.
    users_found = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="users",
        entity_version=ENTITY_VERSION,
        condition={"username": data.username}
    )
    # Check each candidate’s password.
    for user in users_found:
        if user.get("password") == data.password:  # TODO: Use secure password validation
            return jsonify({'token': 'JWT', 'user_id': user.get("user_id")})
    return jsonify({'error': 'Invalid credentials'}), 401


@app.route('/posts', methods=['POST'])
@validate_request(PostCreate)
async def create_post(data: PostCreate):
    post_id = str(uuid4())
    # Prepare the post record.
    post_entity = {
        'post_id': post_id,
        'title': data.title,
        'tags': [tag.strip() for tag in data.tags.split(',')],  # simple splitting of comma-separated tags
        'body': data.body,
        'upvotes': 0,
        'downvotes': 0,
        'user_id': data.user_id  # TODO: derive user_id from token in production
    }
    await entity_service.add_item(
        token=cyoda_token,
        entity_model="posts",
        entity_version=ENTITY_VERSION,
        entity=post_entity
    )
    return jsonify({'post_id': post_id, 'message': 'Post created successfully.'})


@app.route('/posts', methods=['GET'])
async def get_posts():
    posts_list = await entity_service.get_items(
        token=cyoda_token,
        entity_model="posts",
        entity_version=ENTITY_VERSION,
    )
    return jsonify({'posts': posts_list, 'total': len(posts_list)})


@app.route('/posts/<post_id>', methods=['GET'])
async def get_post(post_id):
    post = await entity_service.get_item(
        token=cyoda_token,
        entity_model="posts",
        entity_version=ENTITY_VERSION,
        technical_id=post_id
    )
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    return jsonify(post)


@app.route('/posts/<post_id>', methods=['DELETE'])
async def delete_post(post_id):
    post = await entity_service.get_item(
        token=cyoda_token,
        entity_model="posts",
        entity_version=ENTITY_VERSION,
        technical_id=post_id
    )
    if post:
        await entity_service.delete_item(
            token=cyoda_token,
            entity_model="posts",
            entity_version=ENTITY_VERSION,
            entity=post,
            meta={}
        )
        return jsonify({'message': 'Post deleted successfully.'})
    return jsonify({'error': 'Post not found'}), 404


@app.route('/posts/<post_id>/comments', methods=['POST'])
@validate_request(CommentCreate)
async def add_comment(data: CommentCreate, post_id):
    # First check that the post exists.
    post = await entity_service.get_item(
        token=cyoda_token,
        entity_model="posts",
        entity_version=ENTITY_VERSION,
        technical_id=post_id
    )
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    comment_id = str(uuid4())
    comment_entity = {
        'comment_id': comment_id,
        'body': data.body,
        'post_id': post_id,
        'upvotes': 0,
        'downvotes': 0,
        'user_id': data.user_id  # TODO: derive user_id from token in production
    }
    await entity_service.add_item(
        token=cyoda_token,
        entity_model="comments",
        entity_version=ENTITY_VERSION,
        entity=comment_entity
    )
    return jsonify({'comment_id': comment_id, 'message': 'Comment added successfully.'})


@app.route('/posts/<post_id>/comments', methods=['GET'])
async def get_comments(post_id):
    # Confirm that the post exists.
    post = await entity_service.get_item(
        token=cyoda_token,
        entity_model="posts",
        entity_version=ENTITY_VERSION,
        technical_id=post_id
    )
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    # Get comments matching the post_id.
    post_comments = await entity_service.get_items_by_condition(
        token=cyoda_token,
        entity_model="comments",
        entity_version=ENTITY_VERSION,
        condition={"post_id": post_id}
    )
    return jsonify({'comments': post_comments})


@app.route('/posts/<post_id>/comments/<comment_id>', methods=['DELETE'])
async def delete_comment(post_id, comment_id):
    # Try to retrieve the comment.
    comment = await entity_service.get_item(
        token=cyoda_token,
        entity_model="comments",
        entity_version=ENTITY_VERSION,
        technical_id=comment_id
    )
    if comment:
        await entity_service.delete_item(
            token=cyoda_token,
            entity_model="comments",
            entity_version=ENTITY_VERSION,
            entity=comment,
            meta={}
        )
        return jsonify({'message': 'Comment deleted successfully.'})
    return jsonify({'error': 'Comment not found'}), 404


@app.route('/posts/<post_id>/images', methods=['POST'])
@validate_request(ImageUpload)
async def upload_image(data: ImageUpload, post_id):
    # NOTE: In a real scenario, this endpoint would handle file uploads appropriately.
    image_id = str(uuid4())
    image_entity = {
        'image_id': image_id,
        'post_id': post_id,
        'image_url': 'mock_image_url'
    }
    await entity_service.add_item(
        token=cyoda_token,
        entity_model="images",
        entity_version=ENTITY_VERSION,
        entity=image_entity
    )
    return jsonify({'image_id': image_id, 'message': 'Image uploaded successfully.'})


@app.route('/posts/<post_id>/images/<image_id>', methods=['GET'])
async def get_image(post_id, image_id):
    image = await entity_service.get_item(
        token=cyoda_token,
        entity_model="images",
        entity_version=ENTITY_VERSION,
        technical_id=image_id
    )
    if not image or image.get('post_id') != post_id:
        return jsonify({'error': 'Image not found'}), 404
    return jsonify({'image_url': image.get('image_url')})


@app.route('/posts/<post_id>/vote', methods=['POST'])
@validate_request(VoteRequest)
async def vote_post(data: VoteRequest, post_id):
    post = await entity_service.get_item(
        token=cyoda_token,
        entity_model="posts",
        entity_version=ENTITY_VERSION,
        technical_id=post_id
    )
    if not post:
        return jsonify({'error': 'Post not found'}), 404

    # Update the vote tally.
    if data.vote == 'up':
        post['upvotes'] = post.get('upvotes', 0) + 1
    elif data.vote == 'down':
        post['downvotes'] = post.get('downvotes', 0) + 1
    else:
        return jsonify({'error': 'Invalid vote value'}), 400

    await entity_service.update_item(
        token=cyoda_token,
        entity_model="posts",
        entity_version=ENTITY_VERSION,
        entity=post,
        meta={}
    )
    return jsonify({'message': 'Vote recorded.'})


@app.route('/posts/<post_id>/comments/<comment_id>/vote', methods=['POST'])
@validate_request(VoteRequest)
async def vote_comment(data: VoteRequest, post_id, comment_id):
    comment = await entity_service.get_item(
        token=cyoda_token,
        entity_model="comments",
        entity_version=ENTITY_VERSION,
        technical_id=comment_id
    )
    if not comment:
        return jsonify({'error': 'Comment not found'}), 404

    if data.vote == 'up':
        comment['upvotes'] = comment.get('upvotes', 0) + 1
    elif data.vote == 'down':
        comment['downvotes'] = comment.get('downvotes', 0) + 1
    else:
        return jsonify({'error': 'Invalid vote value'}), 400

    await entity_service.update_item(
        token=cyoda_token,
        entity_model="comments",
        entity_version=ENTITY_VERSION,
        entity=comment,
        meta={}
    )
    return jsonify({'message': 'Vote recorded.'})


if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
------------------------------------------------------------

Key notes:
• Every direct interaction with a local cache (the dictionaries) is now replaced by a corresponding call to entity_service.
• The endpoints remain the same and all existing business logic (data ingestion, validations, vote tally updates, etc.) is preserved.
• In the login endpoint, the external service is queried by a condition to find matching usernames.
• The startup function now initializes cyoda with the provided token before the server starts serving.
• Where the external service does not directly provide all needed semantics (for instance, lookups by condition or existence checks), we use the provided functions to simulate those behaviors.