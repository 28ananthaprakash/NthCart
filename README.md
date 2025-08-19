# Overview

NthCart is a shopping cart application that offers a unique discount system where every nth order receives a discount. The application is built using FastAPI.

# API Endpoints

`/login` - Authenticates a user and returns a JWT token. (Supports both user and admin)
- `GET /items` - List available items 
- `POST /cart/add` - Add item to cart 
- `GET /cart` - View expanded cart with line totals and cart total
- `POST /cart/checkout` - Checkout cart (Assuming the user will make the payment without fail). discount code as optional
- `POST /admin/generate_discount` -  Generates a single-use coupon for the user (Admin Only)
- `GET /admin/stats` - Returns per-user stats. Use `?email=...` to scope stats to a single user by email. 

# Installation 

1. Clone the repository and activate the virtual environment if needed
2. Install the requirements by running `pip install -r requirements.txt`
3. Run `fastapi dev` to start the development server
4. (Optional) To host it, you can use a production server like Uvicorn or Gunicorn.

# Potential Improvements

1. Given the requirements are simple, I've used handlers.py and models.py. But I strongly recommend Ruby on Rails folder structure as a blueprint or a better structure (for example, event driven architecture) if the requirement has the potential to grow.
2. To improve the security and logging, middlewares can be a useful addition. 
3. Add a feature for the user to see available coupons and complete CRUD for the current APIs
