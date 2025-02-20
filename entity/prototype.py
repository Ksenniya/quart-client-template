# Here's a prototype implementation of your Quart application based on the requirements you've provided. This code uses local cache for persistence and mocks any external APIs. It includes placeholders where details are uncertain. 
# 
# ```python
from quart import Quart, jsonify, request
from quart_schema import QuartSchema
from uuid import uuid4

app = Quart(__name__)
QuartSchema(app)

# In-memory data storage (mocking persistence)
users = {}
posts = {}
comments = {}
images = {}

@app.route('/users', methods=['POST'])
async def create_user():
    data = await request.get_json()
    user_id = str(uuid4())
    users[user_id] = {'username': data['username'], 'password': data['password']}  # TODO: Hash the password
    return jsonify({'token': 'JWT', 'user_id': user_id})

@app.route('/users/login', methods=['POST'])
async def login_user():
    data = await request.get_json()
    for user_id, user in users.items():
        if user['username'] == data['username'] and user['password'] == data['password']:  # TODO: Validate password properly
            return jsonify({'token': 'JWT', 'user_id': user_id})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/posts', methods=['POST'])
async def create_post():
    data = await request.get_json()
    post_id = str(uuid4())
    posts[post_id] = {
        'post_id': post_id,
        'title': data['title'],
        'tags': data['tags'],
        'body': data['body'],
        'upvotes': 0,
        'downvotes': 0,
        'user_id': data.get('user_id')  # TODO: Get user_id from token
    }
    return jsonify({'post_id': post_id, 'message': 'Post created successfully.'})

@app.route('/posts', methods=['GET'])
async def get_posts():
    return jsonify({'posts': list(posts.values()), 'total': len(posts)})

@app.route('/posts/<post_id>', methods=['GET'])
async def get_post(post_id):
    post = posts.get(post_id)
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    return jsonify(post)

@app.route('/posts/<post_id>', methods=['DELETE'])
async def delete_post(post_id):
    if post_id in posts:
        del posts[post_id]
        return jsonify({'message': 'Post deleted successfully.'})
    return jsonify({'error': 'Post not found'}), 404

@app.route('/posts/<post_id>/comments', methods=['POST'])
async def add_comment(post_id):
    if post_id not in posts:
        return jsonify({'error': 'Post not found'}), 404
    data = await request.get_json()
    comment_id = str(uuid4())
    comments[comment_id] = {
        'comment_id': comment_id,
        'body': data['body'],
        'post_id': post_id,
        'upvotes': 0,
        'downvotes': 0,
        'user_id': data.get('user_id')  # TODO: Get user_id from token
    }
    return jsonify({'comment_id': comment_id, 'message': 'Comment added successfully.'})

@app.route('/posts/<post_id>/comments', methods=['GET'])
async def get_comments(post_id):
    if post_id not in posts:
        return jsonify({'error': 'Post not found'}), 404
    post_comments = [comment for comment in comments.values() if comment['post_id'] == post_id]
    return jsonify({'comments': post_comments})

@app.route('/posts/<post_id>/comments/<comment_id>', methods=['DELETE'])
async def delete_comment(post_id, comment_id):
    if comment_id in comments:
        del comments[comment_id]
        return jsonify({'message': 'Comment deleted successfully.'})
    return jsonify({'error': 'Comment not found'}), 404

@app.route('/posts/<post_id>/images', methods=['POST'])
async def upload_image(post_id):
    # TODO: Implement image upload handling
    image_id = str(uuid4())
    images[image_id] = {'post_id': post_id, 'image_url': 'mock_image_url'}  # Placeholder for image URL
    return jsonify({'image_id': image_id, 'message': 'Image uploaded successfully.'})

@app.route('/posts/<post_id>/images/<image_id>', methods=['GET'])
async def get_image(post_id, image_id):
    # TODO: Implement image retrieval logic
    image = images.get(image_id)
    if not image or image['post_id'] != post_id:
        return jsonify({'error': 'Image not found'}), 404
    return jsonify({'image_url': image['image_url']})

@app.route('/posts/<post_id>/vote', methods=['POST'])
async def vote_post(post_id):
    data = await request.get_json()
    if post_id not in posts:
        return jsonify({'error': 'Post not found'}), 404
    if data['vote'] == 'up':
        posts[post_id]['upvotes'] += 1
    elif data['vote'] == 'down':
        posts[post_id]['downvotes'] += 1
    return jsonify({'message': 'Vote recorded.'})

@app.route('/posts/<post_id>/comments/<comment_id>/vote', methods=['POST'])
async def vote_comment(post_id, comment_id):
    data = await request.get_json()
    if comment_id not in comments:
        return jsonify({'error': 'Comment not found'}), 404
    if data['vote'] == 'up':
        comments[comment_id]['upvotes'] += 1
    elif data['vote'] == 'down':
        comments[comment_id]['downvotes'] += 1
    return jsonify({'message': 'Vote recorded.'})

if __name__ == '__main__':
    app.run(use_reloader=False, debug=True, host='0.0.0.0', port=8000, threaded=True)
# ```
# 
# ### Key Points
# - The application includes in-memory storage for users, posts, comments, and images, simulating persistence.
# - Each endpoint's implementation follows the specifications you provided, with basic error handling.
# - TODO comments indicate areas where further implementation is necessary, such as password hashing and image handling.
# - The application is designed to run locally on port 8000.
# 
# This prototype allows for a user experience check and helps identify any gaps in the requirements before further development. If you have any additional requests or modifications, feel free to ask!