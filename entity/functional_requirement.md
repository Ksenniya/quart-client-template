# Final Functional Requirements

This document outlines the functional requirements for the backend application, including necessary API endpoints and their specifications.

## 1. User Authentication

### 1.1 Create User
- **Endpoint:** `POST /users/create`
- **Description:** Creates a new user.
- **Request Format:**
  ```json
  {
    "username": "string",
    "email": "string",
    "password": "string"
  }
  ```
- **Response Format:**
  ```json
  {
    "user_id": "string",
    "username": "string",
    "email": "string",
    "message": "User created successfully."
  }
  ```

### 1.2 Login
- **Endpoint:** `POST /users/login`
- **Description:** Authenticates the user and returns a JWT token.
- **Request Format:**
  ```json
  {
    "email": "string",
    "password": "string"
  }
  ```
- **Response Format:**
  ```json
  {
    "user_id": "string",
    "token": "jwt-token-string",
    "message": "Login successful."
  }
  ```

## 2. Post Management

### 2.1 Create Post
- **Endpoint:** `POST /posts`
- **Description:** Creates a new post.
- **Request Format:**
  ```json
  {
    "title": "string",
    "topics": ["string"],
    "body": "string",
    "images": ["optional_image_id_string"]
  }
  ```
- **Response Format:**
  ```json
  {
    "post_id": "string",
    "title": "string",
    "user_id": "string",
    "topics": ["string"],
    "upvotes": 0,
    "downvotes": 0,
    "body": "string",
    "message": "Post created successfully."
  }
  ```

### 2.2 Retrieve Posts (Paginated)
- **Endpoint:** `GET /posts?limit={number}&offset={number}`
- **Description:** Retrieves a paginated list of posts.
- **Response Format:**
  ```json
  {
    "posts": [
      {
        "post_id": "string",
        "title": "string",
        "user_id": "string",
        "topics": ["string"],
        "upvotes": 0,
        "downvotes": 0,
        "body": "string"
      }
    ],
    "limit": 20,
    "offset": 0,
    "total": 100
  }
  ```

### 2.3 Retrieve Specific Post
- **Endpoint:** `GET /posts/{post_id}`
- **Description:** Retrieves a specific post.
- **Response Format:**
  ```json
  {
    "post_id": "string",
    "title": "string",
    "user_id": "string",
    "topics": ["string"],
    "upvotes": 0,
    "downvotes": 0,
    "body": "string"
  }
  ```

### 2.4 Delete Post
- **Endpoint:** `DELETE /posts/{post_id}`
- **Description:** Deletes a post (only by its owner).
- **Response Format:**
  ```json
  {
    "post_id": "string",
    "message": "Post deleted successfully."
  }
  ```

### 2.5 Vote on Post
- **Endpoint:** `POST /posts/{post_id}/vote`
- **Description:** Upvotes or downvotes a post.
- **Request Format:**
  ```json
  {
    "user_id": "string",
    "vote": "up" // or "down"
  }
  ```
- **Response Format:**
  ```json
  {
    "post_id": "string",
    "upvotes": 10,
    "downvotes": 2,
    "message": "Vote recorded."
  }
  ```

## 3. Comment Management

### 3.1 Add Comment
- **Endpoint:** `POST /posts/{post_id}/comments`
- **Description:** Adds a comment to a post.
- **Request Format:**
  ```json
  {
    "user_id": "string",
    "body": "string"
  }
  ```
- **Response Format:**
  ```json
  {
    "comment_id": "number",
    "post_id": "string",
    "user_id": "string",
    "body": "string",
    "upvotes": 0,
    "downvotes": 0,
    "message": "Comment added successfully."
  }
  ```

### 3.2 Retrieve Comments (Paginated)
- **Endpoint:** `GET /posts/{post_id}/comments?limit={number}&offset={number}`
- **Description:** Retrieves a paginated list of comments for a post in chronological order.
- **Response Format:**
  ```json
  {
    "post_id": "string",
    "comments": [
      {
        "comment_id": "number",
        "body": "string",
        "user_id": "string",
        "upvotes": 0,
        "downvotes": 0
      }
    ],
    "limit": 20,
    "offset": 0,
    "total": 50
  }
  ```

### 3.3 Delete Comment
- **Endpoint:** `DELETE /posts/{post_id}/comments/{comment_id}`
- **Description:** Deletes a comment (only by its owner).
- **Response Format:**
  ```json
  {
    "comment_id": "number",
    "message": "Comment deleted successfully."
  }
  ```

### 3.4 Vote on Comment
- **Endpoint:** `POST /posts/{post_id}/comments/{comment_id}/vote`
- **Description:** Upvotes or downvotes a comment.
- **Request Format:**
  ```json
  {
    "user_id": "string",
    "vote": "up" // or "down"
  }
  ```
- **Response Format:**
  ```json
  {
    "comment_id": "number",
    "upvotes": 5,
    "downvotes": 1,
    "message": "Vote recorded."
  }
  ```

## 4. Image Management

### 4.1 Upload Image
- **Endpoint:** `POST /posts/{post_id}/images`
- **Description:** Uploads an image for a post.
- **Request Format:**
  ```json
  {
    "user_id": "string",
    "image_data": "base64-encoded-string",
    "metadata": {
      "filename": "image.jpg",
      "content_type": "image/jpeg"
    }
  }
  ```
- **Response Format:**
  ```json
  {
    "image_id": "string",
    "message": "Image uploaded successfully."
  }
  ```

### 4.2 Retrieve Image
- **Endpoint:** `GET /posts/{post_id}/images/{image_id}`
- **Description:** Retrieves the specified image.
- **Response Format:**  
  The response will be the raw image data served with the appropriate content type.

---

These functional requirements will guide the development of the backend application, ensuring clarity and consistency in the implementation of API endpoints.