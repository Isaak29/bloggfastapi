import firebase_admin
from firebase_admin import credentials, auth, exceptions
from fastapi import FastAPI, HTTPException, Body,Form, status, UploadFile, File, Path, Request
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from starlette.responses import JSONResponse
from bson import ObjectId
from fastapi import FastAPI, Query, Depends
import logging
from typing import Dict
import base64
from fastapi.middleware.cors import CORSMiddleware
from pymongo import DESCENDING
from typing import List, Dict
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import random
import pyrebase
import requests
import random
import secrets
import time

app = FastAPI()
cred = credentials.Certificate('firebase_keys/serviceAccountKey.json')
firebase_admin.initialize_app(cred)
auth_admin = auth
firebaseConfig = {
  "apiKey": "AIzaSyA29uspF0zLxU61-LAZYC5ozbdHESTglB4",
  "authDomain": "taskproject-14c55.firebaseapp.com",
  "databaseURL": "https://taskproject-14c55-default-rtdb.firebaseio.com",
  "projectId": "taskproject-14c55",
  "storageBucket": "taskproject-14c55.appspot.com",
  "messagingSenderId": "1049855100695",
  "appId": "1:1049855100695:web:a8ae5b9a1236937b849952",
  "measurementId": "G-CQ0TGWY94L"
}
firebase = pyrebase.initialize_app(firebaseConfig)




# Pyrebase authentication
auth1 = firebase.auth()

# Connect to MongoDB
mongo_client = AsyncIOMotorClient("mongodb+srv://isaak:cluster29@bloggon.1uiaxcx.mongodb.net/")
db = mongo_client['BloggOn']
blog_collection = db['users'] 


class User(BaseModel):
    email: str
    password: str

class Paragraph(BaseModel):
    user_id: str
    paragraph: str

# CORS configuration to allow requests from your React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://192.168.1.12:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class User(BaseModel):
    name:str
    email:str
    password:str

class UserCredentials(BaseModel):
    email: str
    password: str    

@app.post('/register_user')
async def register_user(user: User):
    try:
        print("userpassword", user.password)
        print("username", user.name)
        print("useremail", user.email)

        # Register user in Firebase using Firebase Admin SDK
        # Note: The user object returned by create_user may not have name attribute.
        user_firebase = auth_admin.create_user(email=user.email, password=user.password)
        
        # The 'user_firebase' object contains information about the created Firebase user.
        # You may access it as follows:
        firebase_user_id = user_firebase.uid
        firebase_user_email = user_firebase.email
        
        print("Firebase user ID:", firebase_user_id)
        print("Firebase user email:", firebase_user_email)
    
        user_data = {
            "name": user.name,  # This may not be present in 'user_firebase'
            "email": user.email,
            "user_id": firebase_user_id
        }
        print("user_data", user_data)
        blog_collection.insert_one(user_data)

        return JSONResponse(content={"message": "User registered successfully", "user_id": firebase_user_id})
    except Exception as e:
        print("error",e)
        raise HTTPException(status_code=400, detail="Registration failed")







@app.post("/verify_login")
async def verify_login(credentials: UserCredentials):
    try:
        # Sign in user with email and password
        user = auth1.sign_in_with_email_and_password(credentials.email, credentials.password)

        # Get user information from Firebase
        user_info = auth1.get_account_info(user['idToken'])

        # Extract email and UID
        user_email = user_info['users'][0]['email']

        # Check if the user with this email exists in Firebase Admin
        try:
            print("+++++++++++")
            user_record = auth_admin.get_user_by_email(credentials.email)
            user_id = user_record.uid
            print("user_record",user_record)
        except auth_admin.UserNotFoundError:
            print("=======")
            # If the user does not exist in Firebase Admin, raise a custom exception
            raise HTTPException(status_code=400, detail="User not found. Please register first.")

        # Return user's email and UID (if available)
        return {"user_email": user_email, "user_id": user_id}
    except requests.exceptions.HTTPError as e:
        # Check if the error is due to wrong password
        if "INVALID_PASSWORD" in str(e):
            raise HTTPException(status_code=401, detail="Invalid password")
        elif "Unauthorized" in str(e):
            raise HTTPException(status_code=401, detail="Unauthorized")
        else:
            raise HTTPException(status_code=401, detail="Authentication failed")

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str

class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str
# Dictionary to store OTPs temporarily
otp_tokens = {}

# Model for request data


class VerifyOTPRequest(BaseModel):
    email: str
    otp: str

# Function to generate a random 6-digit OTP
def generate_otp():
    otp = ''.join(secrets.choice('0123456789') for _ in range(6))
    timestamp = int(time.time())  # Get the current timestamp in seconds
    otp_with_timestamp = f"{otp}:{timestamp}"
    return otp_with_timestamp

# Function to send OTP email
def send_otp_email(email, otp):
    try:
        sender_email = "akmohamedisaakmuzamil29@gmail.com"  # Replace with your sender email address
        sender_password = "bxfzvsgiohuungwn"  # Replace with your sender email app password

        subject = "OTP Verification"
        message = f"Your OTP for verification is: {otp}"

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, email, msg.as_string())
        server.quit()

    except Exception as e:
        print("Error sending OTP email:", e)

class SendOTPRequest(BaseModel):
    email: str
# Endpoint to send OTP
@app.post("/send_otp")
async def send_otp(request_data: SendOTPRequest):
    email = request_data.email

    try:
        # Check if the email exists in Firebase Authentication
        user = auth.get_user_by_email(email)

        # Generate a new OTP token for the email and store it temporarily
        otp = generate_otp()
        otp_tokens[email] = otp

        # Send the OTP email
        send_otp_email(email, otp)

        return {"message": "OTP sent successfully"}
    except auth.UserNotFoundError:
        return {"message": "Email not found in Firebase Authentication"}
# Endpoint to verify OTP
@app.post("/verify_otp")
async def verify_otp(request_data: VerifyOTPRequest):
    email = request_data.email
    entered_otp = request_data.otp

    # Check if the OTP token exists in the dictionary
    if email not in otp_tokens:
        raise HTTPException(status_code=400, detail="Invalid OTP token")

    # Retrieve the stored OTP
    stored_otp = otp_tokens[email]

    # Verify if the entered OTP matches the stored OTP
    if entered_otp == stored_otp:
        return {"message": "OTP verified successfully"}
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP")


@app.post("/reset_password")
async def reset_password(request_data: ResetPasswordRequest):
    try:
        email = request_data.email
        new_password = request_data.new_password
        print("Received reset password request:", request_data)

        # Check if the OTP token exists in the dictionary
        if email not in otp_tokens:
            raise HTTPException(status_code=400, detail="Invalid OTP token")
        
        # Retrieve the OTP token from the dictionary
        token = otp_tokens.pop(email)
            
        # Retrieve the user's UID using the email address
        user = auth.get_user_by_email(email)
        uid = user.uid

        # Use the UID to update the user's password using Firebase Admin SDK
        auth.update_user(uid=uid, password=new_password)

        # Return a JSON response indicating success
        return JSONResponse(content={"message": "Password updated successfully"})

    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=400, detail="Password update failed")




class User(BaseModel):
    username: str
    password: str

import logging

logging.basicConfig(level=logging.INFO)

from bson import ObjectId

class Blog(BaseModel):
    title: str
    blog_text: str
    user_id: str
    category: str
    tags: List[str] 
    summary:str


from datetime import datetime

@app.post("/store_blog")
async def store_blog(blog: Blog):
    blog_id = ObjectId()  # Generate a unique ObjectId for the blog post

    blog_data = {
        "_id": blog_id,
        "title": blog.title,
        "blog_text": blog.blog_text,
        "category": blog.category,
        "tags": blog.tags,
        "summary": blog.summary,
        "created_at": datetime.now(),  # Add the current date and time
        "user_id": blog.user_id  # Assuming user_id is needed in the document
    }

    # Check if the user has existing blogs
    user_blog = await blog_collection.find_one({"user_id": blog.user_id})
    if user_blog:
        # User already has blogs, add the new blog post to their existing blogs
        await blog_collection.update_one(
            {"user_id": blog.user_id},
            {"$push": {"blogs": blog_data}}
        )
    else:
        # User doesn't have blogs, create a new user document with the blog post
        user_data = {
            "user_id": blog.user_id,
            "blogs": [blog_data]
        }
        await blog_collection.insert_one(user_data)

    return {"message": "Blog stored successfully"}


@app.post("/publish_blog/{user_id}/{draft_id}")
async def publish_blog(user_id: str, draft_id: str):
    print(f"Received request to publish_blog with user_id={user_id} and draft_id={draft_id}")
    user_blog = await blog_collection.find_one({"user_id": user_id})

    if user_blog:
        draft_to_publish = None
        for blog in user_blog.get("drafts", []):
            if str(blog["_id"]) == draft_id:
                draft_to_publish = blog
                break

        if draft_to_publish:
            user_blog.setdefault("blogs", []).append(draft_to_publish)
            user_blog["drafts"].remove(draft_to_publish)

            await blog_collection.update_one(
                {"user_id": user_id},
                {"$set": {"blogs": user_blog["blogs"], "drafts": user_blog.get("drafts", [])}}
            )

            return {"message": "Draft published successfully"}
    
    return {"message": "Draft not found"}



@app.post("/save_draft")
async def save_draft(blog: Blog):
    blog_id = ObjectId()  # Generate a unique ObjectId for the draft

    draft_data = {
        "_id": blog_id,
        "title": blog.title,
        "blog_text": blog.blog_text,
        "category": blog.category,
        "tags": blog.tags
    }
    
    # Check if the user has existing drafts
    user_drafts = await blog_collection.find_one({"user_id": blog.user_id})
    if user_drafts:
        # User already has drafts, add the new draft to their existing drafts
        await blog_collection.update_one(
            {"user_id": blog.user_id},
            {"$push": {"drafts": draft_data}}
        )
    else:
        # User doesn't have drafts, create a new user document with the draft
        user_data = {
            "user_id": blog.user_id,
            "drafts": [draft_data]
        }
        await blog_collection.insert_one(user_data)

    return {"message": "Draft saved successfully"}


# 

from bson import ObjectId


from bson import Binary
@app.get("/get_user_blogs")
async def get_user_blogs(user_id: str):
    try:
        user_blog = await blog_collection.find_one({"user_id": user_id})
        user_email = auth.get_user(user_id).email if user_id else None
        print("user_email",user_email)
        root_document = await blog_collection.find_one({"user_id": user_id})
        if root_document:
            root_user_name = root_document.get("name", "Unknown")
            print("root_user_name",root_user_name)
        else:
            root_user_name = "Unknown"
        if user_blog:
            user_blogs = user_blog.get("blogs", [])

            user_blogs_decoded = []
            for blog in user_blogs:
                likes = blog.get("likes", [])
                comments = blog.get("comments", [])

                formatted_likes = [{"user_id": like["user_id"], "user_email": like["user_email"]} for like in likes]
                formatted_comments = [{"user_id": comment["user_id"], "user_email": comment["user_email"], "comment": comment["comment"]} for comment in comments]
                

                blog_data = {
                    "_id": str(blog["_id"]),
                    "user_email":user_email, 
                    "title": blog["title"],
                    "category":blog["category"],
                    "blog_text": blog["blog_text"],
                    
                    "tags":blog["tags"],
                    "likes": formatted_likes,
                    "comments": formatted_comments
                }
                user_blogs_decoded.append(blog_data)

            print("root",root_user_name)
            return {"user_blogs": user_blogs_decoded, "user_name": root_user_name}
        else:
           
            return {"user_blogs": []}
    except Exception as e:
        return {"error": "Error fetching user blogs", "details": str(e)}


class ProfileUpdate(BaseModel):
    user_id: str
    new_profile_pic: str
    new_bio: str
    new_links: str

# Simulated database storage
users = {}

@app.post("/update_user_profile")
async def update_user_profile(profile: ProfileUpdate):
    user_id = profile.user_id
    if user_id:
        root_document = await blog_collection.find_one({"user_id": user_id})
        if root_document:
            root_user_name = root_document.get("name", "Unknown")
            print("root_user",root_user_name)
        user = blog_collection.find_one({'user_id': user_id})
        if user:
            update_data = {
                'profile_pic': profile.new_profile_pic,
                'bio': profile.new_bio,
                'links': profile.new_links
            }
            blog_collection.update_one({'user_id': user_id}, {'$set': update_data})
            return JSONResponse(content={"message": "Profile updated successfully"}, status_code=200)
        else:
            raise HTTPException(status_code=404, detail=f"User with user_id {user_id} not found")
    else:
        raise HTTPException(status_code=400, detail="User_id is missing in the request")



def convert_object_ids_to_strings(user_blogs):
    for blog in user_blogs:
        blog["_id"] = str(blog["_id"])
    return user_blogs

from datetime import datetime, timezone, timedelta
import pytz  # Make sure to install the pytz library if you haven't already
def calculate_timestamp_display(created_at: datetime, user_timezone: str) -> str:
    # Convert the datetime to the user's time zone
    user_timezone = pytz.timezone(user_timezone)
    created_at_local = created_at.astimezone(user_timezone)

    # Calculate the current local time
    current_local_time = datetime.now(user_timezone)

    # Calculate the time difference
    time_difference = current_local_time - created_at_local

    # Calculate minutes, hours, and days
    minutes_difference = int(time_difference.total_seconds() / 60)
    hours_difference = int(minutes_difference / 60)
    days_difference = int(hours_difference / 24)

    if minutes_difference < 1:
        return "Just now"
    elif minutes_difference < 60:
        return f"{minutes_difference} minute{'s' if minutes_difference > 1 else ''} ago"
    elif hours_difference < 24:
        return f"{hours_difference} hour{'s' if hours_difference > 1 else ''} ago"
    elif days_difference == 1:
        return "1 day ago"
    elif days_difference < 30:
        return f"{days_difference} days ago"
    else:
        return created_at_local.strftime("%m-%d")






@app.get("/get_all_blogs")
async def get_all_blogs():
    try:
        all_blogs = await blog_collection.find().sort("created_at", DESCENDING).to_list(length=None)
        all_blogs_decoded = []

        for user_blog in all_blogs:
            user_id = user_blog.get("user_id")
            user_email = auth.get_user(user_id).email if user_id else None
            name = user_blog.get("name")
            user_blogs = user_blog.get("blogs", [])

            for blog in user_blogs:
                # Calculate the timestamp display
                created_at = blog.get("created_at")
                user_timezone = 'Asia/Kolkata'  # Replace with the user's time zone
                timestamp_display = calculate_timestamp_display(created_at, user_timezone)

                likes = blog.get("likes", [])
                comments = blog.get("comments", [])

                formatted_likes = [{"user_id": like["user_id"], "user_email": like["user_email"]} for like in likes]
                formatted_comments = [{"comment_id": str(comment["_id"]), "user_id": comment["user_id"], "user_email": comment["user_email"], "comment": comment["comment"]} for comment in comments]

                blog_data = {
                    "_id": str(blog["_id"]),
                    "user_id": user_id,
                    "name": name,
                    "user_email": user_email,
                    "title": blog["title"],
                    "category": blog["category"],
                    "blog_text": blog["blog_text"],
                    "tags": blog["tags"],
                    "summary": blog["summary"],
                    "likes": formatted_likes,
                    "comments": formatted_comments,
                    "timestamp_display": timestamp_display  # Include the timestamp display
                }
                all_blogs_decoded.append(blog_data)

        # Print the timestamp_display values for debugging
        for blog_data in all_blogs_decoded:
            print(f"Timestamp Display: {blog_data['timestamp_display']}")

        # Sort the blogs by timestamp in descending order (most recent first)
        all_blogs_decoded.sort(key=lambda x: (
            0 if "hour" in x['timestamp_display'] else 1, x['timestamp_display']), reverse=False)

        # Print the sorted timestamp_display values for debugging
        for blog_data in all_blogs_decoded:
            print(f"Sorted Timestamp Display: {blog_data['timestamp_display']}")

        return {"all_blogs": all_blogs_decoded}
    except Exception as e:
        return {"error": "Error fetching all blogs", "details": str(e)}


class SubscriptionData(BaseModel):
    user_id: str
    category: str

@app.post("/subscribe/{user_id}/{category}")
async def subscribe(user_id: str, category: str):
    # Check if the user is already subscribed to the category
    user = await blog_collection.find_one({"user_id": user_id})
    if user and category in user.get("subscribed_categories", []):
        return {"status": "already_subscribed"}

    # Update the user's subscribed categories in the database
    await blog_collection.update_one({"user_id": user_id}, {"$addToSet": {"subscribed_categories": category}}, upsert=True)
    return {"status": "success"}

@app.post("/follow_tag/{user_id}/{tag}")
async def follow_tag(user_id: str, tag: str):
    # Check if the user is already subscribed to the category
    user = await blog_collection.find_one({"user_id": user_id})
    if user and tag in user.get("following_tags", []):
        return {"status": "already_subscribed"}

    # Update the user's subscribed categories in the database
    await blog_collection.update_one({"user_id": user_id}, {"$addToSet": {"following_tags": tag}}, upsert=True)
    return {"status": "success"}  




otp_tokens = {}




@app.post('/like_post/{blog_id}')
async def like_post(blog_id: str, user_id: str = Form(...)):
    try:
        # Check if blog_id is valid
        if not ObjectId.is_valid(blog_id):
            return JSONResponse(content={"message": "Invalid blog_id"}, status_code=400)

        # Retrieve the user's email using the user_id from Firebase or your authentication system
        user_email = auth.get_user(user_id).email  # Implement this function to get the user's email

        blog_id = ObjectId(blog_id)
        result = await blog_collection.update_one(
            {"blogs._id": blog_id},
            {"$addToSet": {"blogs.$.likes": {"user_id": user_id, "user_email": user_email}}}
        )
        if result.modified_count == 1:
            return JSONResponse(content={"message": "Post liked successfully"})
        else:
            blog = await blog_collection.find_one({"blogs._id": blog_id})
            if any(like['user_id'] == user_id for like in blog['blogs'][0]['likes']):
                return JSONResponse(content={"message": "Post already liked by the user"})
            return JSONResponse(content={"message": "Failed to like post"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"message": "Internal server error"}, status_code=500)


@app.post('/unlike_post/{blog_id}')
async def unlike_post(blog_id: str, user_id: str = Form(...)):
    try:
        # Check if blog_id is valid
        if not ObjectId.is_valid(blog_id):
            return JSONResponse(content={"message": "Invalid blog_id"}, status_code=400)

        blog_id = ObjectId(blog_id)

        result = await blog_collection.update_one(
            {"blogs._id": blog_id},
            {"$pull": {"blogs.$.likes": {"user_id": user_id}}}
        )

        if result.modified_count == 1:
            return JSONResponse(content={"message": "Post unliked successfully"})
        else:
            blog = await blog_collection.find_one({"blogs._id": blog_id})
            if any(like['user_id'] == user_id for like in blog['blogs'][0]['likes']):
                return JSONResponse(content={"message": "Post not liked by the user"})
            return JSONResponse(content={"message": "Failed to unlike post"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"message": "Internal server error"}, status_code=500)


    
@app.post('/comment_post/{blog_id}')
async def comment_post(blog_id: str, user_id: str = Form(...), comment: str = Form(...)):
    try:
        blog_id = ObjectId(blog_id)
        user_email = auth.get_user(user_id).email

        comment_id = ObjectId()  # Generate a new ObjectId for the comment
        new_comment = {"_id": comment_id, "user_id": user_id, "user_email": user_email, "comment": comment}

        result = await blog_collection.update_one(
            {"blogs._id": blog_id},
            {"$push": {"blogs.$.comments": new_comment}}
        )
        if result.modified_count == 1:
            return JSONResponse(content={"message": "Comment added successfully"})
        else:
            raise HTTPException(status_code=400, detail="Failed to add comment")
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal server error")


# Define a function to get the likes and comments for a specific blog post
async def get_likes_and_comments(blog_id: str):
    blog = await blog_collection.find_one({"blogs._id": ObjectId(blog_id)})
    if blog:
        for post in blog['blogs']:
            if str(post['_id']) == blog_id:
                return post['likes'], post['comments']
    return [], []

from bson import ObjectId

@app.get("/get_blog/{blog_id}")
async def get_blog(blog_id: str):
    try:
        blog = await blog_collection.find_one({"blogs._id": ObjectId(blog_id)})
        


        if blog:
            target_blog = None
            user_id = blog.get("user_id")
            user_email = auth.get_user(user_id).email if user_id else None
            print("user_email",user_email)


            for blog_data in blog.get("blogs", []):
                if str(blog_data["_id"]) == blog_id:
                    target_blog = blog_data
                    break

            if target_blog:
                likes = blog.get("likes", [])
                comments = blog.get("comments", [])
                formatted_likes = [{"user_id": like["user_id"], "user_email": like["user_email"]} for like in likes]
                formatted_comments = [{"comment_id": str(comment["_id"]), "user_id": comment["user_id"], "user_email": comment["user_email"], "comment": comment["comment"]} for comment in comments]

                blog_data = {
                    "_id": str(target_blog["_id"]),
                    "user_email": user_email,
                    "title": target_blog["title"],
                    "category": target_blog["category"],
                    "blog_text": target_blog["blog_text"],
                    
                    "tags":target_blog["tags"],
                    "likes": formatted_likes,
                    "comments": formatted_comments
                }

                return blog_data
            else:
                return {"error": "Blog not found"}
        else:
            return {"error": "User not found"}
    except Exception as e:
        return {"error": "Error fetching blog", "details": str(e)}


@app.post("/follow_user")
async def follow_user(user_id: str = Form(...), target_user_email: str = Form(...)):

    try:
        # Retrieve the follower's email using the user_id from Firebase or your authentication system
        follower_email = auth.get_user(user_id).email 
        print("follower_email", follower_email)
        print("target_user_email", target_user_email) # Implement this function to get the user's email

        # Retrieve the target user's email from the provided parameter
        target_user_email = target_user_email

        if follower_email == target_user_email:
            return {"message": "You cannot follow yourself"}
        
        try:
            target_user = auth.get_user_by_email(target_user_email)
            target_user_id = target_user.uid
            print("target_user_id", target_user_id)
        except Exception as e:
            return {"error": "Error retrieving target user's UID", "details": str(e)}

        # Fetch the root document for the target user
        target_root_document = await blog_collection.find_one({"user_id": target_user_id}) 
        # Implement this function

        # Check if the follower is already in the target user's followers list
        followers = target_root_document.get("followers", [])
        for follower in followers:
            if follower["user_email"] == follower_email:
                return {"message": "You are already following this user"}

        # Add the follower to the target user's followers list
        followers.append({"user_id": user_id, "user_email": follower_email})
        update_data = {"followers": followers}

        # Update the target user's root document to add the follower
        update_result = await blog_collection.update_one({"user_id": target_user_id}, {"$set": update_data})
        
        if update_result.modified_count == 1:
            return {"message": "User followed successfully"}
        else:
            return {"error": "Error updating target user's root document"}

    except Exception as e:
        return {"error": "Error following user", "details": str(e)}
    
@app.get("/get_edit_blog/{blog_id}")
async def get_edit_blog(blog_id: str):
    try:
        blog = await blog_collection.find_one({"blogs._id": ObjectId(blog_id)})

        if blog:
            target_blog = None
            user_id = blog.get("user_id")
            user_email = auth.get_user(user_id).email if user_id else None

            for blog_data in blog.get("blogs", []):
                if str(blog_data["_id"]) == blog_id:
                    target_blog = blog_data
                    break

            if target_blog:
                blog_data = {
                    "_id": str(target_blog["_id"]),
                    "user_email": user_email,
                    "title": target_blog["title"],
                    "category": target_blog["category"],
                    "blog_text": target_blog["blog_text"],
                    "tags": target_blog["tags"]
                }
                return blog_data
            else:
                raise HTTPException(status_code=404, detail="Blog not found")
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error fetching blog")



@app.post("/update_blog/{blog_id}")
async def update_blog(
    blog_id: str,
    title: str = Form(...),
    category: str = Form(...),
    blog_text: str = Form(...),
    tags: str = Form(...)
):
    try:
        # Update the blog data in the collection using your existing logic
        result = await blog_collection.update_one(
            {"blogs._id": ObjectId(blog_id)},
            {"$set": {"blogs.$.title": title, "blogs.$.category": category, "blogs.$.blog_text": blog_text, "blogs.$.tags": tags}}
        )

        if result.modified_count > 0:
            return {"message": "Blog updated successfully"}
        else:
            return {"error": "No changes made to the blog"}

    except Exception as e:
        return {"error": "Error updating blog", "details": str(e)}
    
@app.delete("/delete_blog/{blog_id}")
async def delete_blog(blog_id: str):
    try:
        # Delete the blog from the collection based on the blog ID
        result = await blog_collection.update_one(
            {"blogs._id": ObjectId(blog_id)},
            {"$pull": {"blogs": {"_id": ObjectId(blog_id)}}}
        )

        if result.modified_count > 0:
            return {"message": "Blog deleted successfully"}
        else:
            return {"error": "No changes made"}

    except Exception as e:
        return {"error": "Error deleting blog", "details": str(e)}    
    
def get_user_id_from_email(email: str) -> str:
    user = auth.get_user_by_email(email)
    return user.uid

@app.post("/save_bookmark")
async def save_bookmark(data: dict):
    user_id_session = data.get("user_id")
    blog_id = data.get("blog_id")
    created_email = data.get("created_email")

    # Fetch user_id using Firebase Admin SDK
    user_id_firebase = get_user_id_from_email(created_email)

    if user_id_firebase != user_id_session:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Fetch the blog data from the "blogs" key of the user's document
    user_document = await blog_collection.find_one({"user_id": user_id_firebase})
    if not user_document:
        raise HTTPException(status_code=404, detail="User not found")

    blog_data = None
    for blog in user_document.get("blogs", []):
        if str(blog["_id"]) == blog_id:
            blog_data = blog
            break

    if not blog_data:
        raise HTTPException(status_code=404, detail="Blog not found")

    # Update the user's document to store the bookmark
    update_result = await blog_collection.update_one(
        {"user_id": user_id_session},
        {"$push": {"bookmarks": blog_data}}
    )

    if update_result.modified_count > 0:
        return {"status": "success", "message": "Blog bookmarked"}
    else:
        raise HTTPException(status_code=500, detail="Bookmark could not be saved")

@app.get("/get_bookmarked_posts")
async def get_bookmarked_posts(user_id: str):
    try:
        user_document = await blog_collection.find_one({"user_id": user_id})
        if user_document:
            user_blogs = user_document.get("bookmarks", [])

            user_blogs_decoded = []
            for blog in user_blogs:
                likes = blog.get("likes", [])
                comments = blog.get("comments", [])

                formatted_likes = [{"user_id": like["user_id"], "user_email": like["user_email"]} for like in likes]
                formatted_comments = [{"user_id": comment["user_id"], "user_email": comment["user_email"], "comment": comment["comment"]} for comment in comments]
                

                blog_data = {
                    "_id": str(blog["_id"]),
            
                    "title": blog["title"],
                    "category":blog["category"],
                    "blog_text": blog["blog_text"],
                    
                    "tags":blog["tags"],
                    "likes": formatted_likes,
                    "comments": formatted_comments
                }
                user_blogs_decoded.append(blog_data)
                
            return {"user_blogs": user_blogs_decoded}
        else:
            return {"user_blogs": []}
    except Exception as e:
        return {"error": "Error fetching user blogs", "details": str(e)}




@app.post('/delete_comment/{blog_id}/{comment_id}')
async def delete_comment(blog_id: str, comment_id: str, user_id: str = Form(...)):
    try:
        blog_id = ObjectId(blog_id)
        comment_id = ObjectId(comment_id)
        
        result = await blog_collection.update_one(
            {"blogs._id": blog_id},
            {"$pull": {"blogs.$.comments": {"_id": comment_id, "user_id": user_id}}}
        )
   
        if result.modified_count == 1:
            return JSONResponse(content={"message": "Comment deleted successfully"})
        else:
            raise HTTPException(status_code=400, detail="Failed to delete comment")
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/unfollow_user")
async def unfollow_user(user_id: str = Form(...), target_user_email: str = Form(...)):
    try:
        follower_email = auth.get_user(user_id).email 
        target_user_email = target_user_email

        try:
            target_user = auth.get_user_by_email(target_user_email)
            target_user_id = target_user.uid
        except Exception as e:
            return {"error": "Error retrieving target user's UID", "details": str(e)}

        target_root_document = await blog_collection.find_one({"user_id": target_user_id})

        followers = target_root_document.get("followers", [])
        updated_followers = [follower for follower in followers if follower["user_email"] != follower_email]

        if len(followers) == len(updated_followers):
            return {"message": "You are not following this user"}

        update_data = {"followers": updated_followers}
        update_result = await blog_collection.update_one({"user_id": target_user_id}, {"$set": update_data})

        if update_result.modified_count == 1:
            return {"message": "User unfollowed successfully"}
        else:
            return {"error": "Error updating target user's root document"}

    except Exception as e:
        return {"error": "Error unfollowing user", "details": str(e)}

@app.post("/unbookmark_blog")
async def unbookmark_blog(user_id: str = Form(...), blog_id: str = Form(...)):
    try:
        user_document = await blog_collection.find_one({"user_id": user_id})
        if user_document:
            blog_to_remove = None
            for blog in user_document.get("bookmarks", []):
                if str(blog["_id"]) == blog_id:
                    blog_to_remove = blog
                    break

            if blog_to_remove:
                updated_bookmarks = [bookmark for bookmark in user_document.get("bookmarks", []) if bookmark != blog_to_remove]
                update_data = {"bookmarks": updated_bookmarks}
                update_result = await blog_collection.update_one({"user_id": user_id}, {"$set": update_data})

                if update_result.modified_count > 0:
                    return {"message": "Blog unbookmarked successfully"}
                else:
                    return {"error": "Error updating user's bookmarks"}
            else:
                return {"message": "Blog not bookmarked by the user"}

        else:
            return {"error": "User not found"}
    except Exception as e:
        return {"error": "Error unbookmarking blog", "details": str(e)}

from bson import ObjectId


from fastapi.encoders import jsonable_encoder

@app.get("/get_all_draft_titles")
async def get_all_draft_titles(user_id: str):
    try:
        user = await blog_collection.find_one({"user_id": user_id})

        if user:
            drafts = user.get("drafts", [])
            draft_titles = [{"_id": str(draft["_id"]), "title": draft["title"]} for draft in drafts]
            return {"draft_titles": draft_titles}
        else:
            return {"draft_titles": []}
    except Exception as e:
        return {"error": "Error fetching draft titles", "details": str(e)}










@app.get("/get_edit_draft/{draft_id}")
async def get_edit_draft(draft_id: str):
    try:
        draft = await blog_collection.find_one({"drafts._id": ObjectId(draft_id)})
        print("draft",draft)

        if draft:
            target_draft = None

            for draft_data in draft.get("drafts", []):
                if str(draft_data["_id"]) == draft_id:
                    target_draft = draft_data
                    break

            if target_draft:
                draft_data = {
                    "_id": str(target_draft["_id"]),
                    "title": target_draft["title"],
                    "category": target_draft["category"],
                    "blog_text": target_draft["blog_text"],
                    "tags": target_draft["tags"]
                }
                return draft_data
            else:
                raise HTTPException(status_code=404, detail="Draft not found")
        else:
            raise HTTPException(status_code=404, detail="Draft not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error fetching draft")




if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="192.168.1.12", port=8000)
