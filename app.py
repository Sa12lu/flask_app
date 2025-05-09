import os
import io
import base64
from markupsafe import Markup  # ✅ CORRECT
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask import send_file
from flask import Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/flask_app'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# File Upload Configuration
UPLOAD_FOLDER = 'static/uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=True)
    description = db.Column(db.String(500), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    priority = db.Column(db.String(10), nullable=False, default='Low')
    image_filename = db.Column(db.String(100), nullable=True)

class SaleProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    image_data = db.Column(db.LargeBinary, nullable=True)  
    image_mimetype = db.Column(db.String(50), nullable=True)  

class PurchasedProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Pending")
    username = db.Column(db.String(150), nullable=False)  # Add this line
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # add NEW time date

class GiftBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gift_name = db.Column(db.String(100), nullable=False)  # Added gift name 
    image_data = db.Column(db.LargeBinary, nullable=True)  #  Stores image in binary
    image_mimetype = db.Column(db.String(50))               # Stores the image file type (JPEG, PNG)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Integer, nullable=False)

class Booked(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gift_name = db.Column(db.String(100), nullable=False)  # ← Add this line
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    datetime = db.Column(db.DateTime, default=datetime.utcnow)
    customer_name = db.Column(db.String(150), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('cust_user.id'))  
    status = db.Column(db.String(50), default='Pending')
    
class CustUser(db.Model):
    __tablename__ = 'cust_user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=True)  # Optional image storage
    image_mimetype = db.Column(db.String(50))
    quantity = db.Column(db.Integer, default=0)

class BuyStock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    datetime = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Username and Password are required.', 'danger')
            return render_template('register.html')

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {e}', 'danger')

    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'])
    else:
        flash('You need to log in first.', 'warning')
        return redirect(url_for('login'))

@app.route('/inventory')
def inventory():
    if 'username' in session:
        products = Product.query.order_by(
            db.case(
                (Product.type == None, "Uncategorized"),
                else_=Product.type
            ),
            db.case(
                (Product.priority == 'High', 1),
                (Product.priority == 'Medium', 2),
                (Product.priority == 'Low', 3),
                else_=4
            ),
            Product.name.asc()
        ).all()

        grouped_products = {}
        for product in products:
            product_type = product.type if product.type else "Uncategorized"
            if product_type not in grouped_products:
                grouped_products[product_type] = []
            grouped_products[product_type].append(product)

        return render_template('inventory.html', grouped_products=grouped_products)
    else:
        flash('You need to log in first.', 'warning')
        return redirect(url_for('login'))

@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    if 'username' in session:
        if request.method == 'POST':
            try:
                name = request.form['name']
                product_type = request.form.get('type', 'Uncategorized')
                description = request.form.get('description', '')
                quantity = int(request.form['quantity'])
                priority = request.form.get('priority', 'Low')
                file = request.files.get('image')

                image_filename = None
                if file and allowed_file(file.filename):
                    image_filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

                new_product = Product(
                    name=name,
                    type=product_type,
                    description=description,
                    quantity=quantity,
                    priority=priority,
                    image_filename=image_filename
                )
                db.session.add(new_product)
                db.session.commit()
                flash('Product added successfully!', 'success')
                return redirect(url_for('inventory'))
            except ValueError:
                flash('Invalid quantity input.', 'danger')

        return render_template('add_product.html')
    flash('You need to log in first.', 'warning')
    return redirect(url_for('login'))

@app.route('/edit-product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'username' in session:
        product = Product.query.get(product_id)
        if not product:
            flash('Product not found.', 'danger')
            return redirect(url_for('inventory'))

        if request.method == 'POST':
            product.name = request.form['name']
            product.type = request.form.get('type', 'Uncategorized')
            product.description = request.form.get('description', '')
            product.quantity = int(request.form['quantity'])
            product.priority = request.form.get('priority', 'Low')

            file = request.files.get('image')
            if file and allowed_file(file.filename):
                image_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                product.image_filename = image_filename

            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('inventory'))

        return render_template('edit_product.html', product=product)
    else:
        flash('You need to log in first.', 'warning')
        return redirect(url_for('login'))

@app.route('/delete-product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'username' in session:
        product = Product.query.get(product_id)
        if product:
            if product.image_filename:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.image_filename)
                if os.path.exists(image_path):
                    os.remove(image_path)

            db.session.delete(product)
            db.session.commit()
            flash('Product deleted successfully!', 'success')
        else:
            flash('Product not found.', 'danger')
        return redirect(url_for('inventory'))
    flash('You need to log in first.', 'warning')
    return redirect(url_for('login'))

@app.route('/add-quantity/<int:product_id>', methods=['POST'])
def add_quantity(product_id):
    if 'username' in session:
        try:
            product = Product.query.get(product_id)
            if not product:
                flash('Product not found.', 'danger')
                return redirect(url_for('inventory'))


            amount = int(request.form['amount'])
            if amount < 0:
                flash('Invalid amount. Please enter a positive number.', 'danger')
            else:
                product.quantity += amount
                db.session.commit()
                flash(f'Successfully added {amount} to {product.name}.', 'success')
        except ValueError:
            flash('Invalid input. Please enter a number.', 'danger')
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
        return redirect(url_for('inventory'))
    else:
        flash('You need to log in first.', 'warning')
        return redirect(url_for('login'))


@app.route('/subtract-quantity/<int:product_id>', methods=['POST'])
def subtract_quantity(product_id):
    if 'username' in session:
        try:
            product = Product.query.get(product_id)
            if not product:
                flash('Product not found.', 'danger')
                return redirect(url_for('inventory'))


            amount = int(request.form['amount'])
            if amount < 0:
                flash('Invalid amount. Please enter a positive number.', 'danger')
            elif product.quantity - amount < 0:
                flash('Insufficient stock.', 'danger')
            else:
                product.quantity -= amount
                db.session.commit()
                flash(f'Successfully subtracted {amount} from {product.name}.', 'success')
        except ValueError:
            flash('Invalid input. Please enter a number.', 'danger')
        except Exception as e:
            flash(f'An error occurred: {e}', 'danger')
        return redirect(url_for('inventory'))
    else:
        flash('You need to log in first.', 'warning')
        return redirect(url_for('login'))
    
@app.route('/sale')
def sale():
    if 'username' in session:
        products = SaleProduct.query.all()
        purchased_products = PurchasedProduct.query.all()
        return render_template('sale.html', products=products, purchased_products=purchased_products)
    else:
        flash('You need to log in first.', 'warning')
        return redirect(url_for('login'))

# Route increase sale product quantity
@app.route('/increase-sale-quantity/<int:product_id>', methods=['POST'])
def increase_sale_quantity(product_id):
    if 'username' in session:
        product = SaleProduct.query.get(product_id)
        if product:
            product.quantity += 1
            db.session.commit()
            return jsonify({'success': True, 'new_quantity': product.quantity})
        return jsonify({'success': False, 'error': 'Product not found'}), 404
    return jsonify({'success': False, 'error': 'Unauthorized'}), 401

@app.route('/add-product-sale', methods=['GET', 'POST'])
def add_product_sale():
    if 'username' in session:  # Check if user is logged in
        if request.method == 'POST':
            name = request.form['name']
            description = request.form.get('description', '')
            price = request.form['price']
            quantity = request.form['quantity']
            file = request.files.get('image')

            try:
                price = float(price)
                quantity = int(quantity)

                image_data = None
                image_mimetype = None

                # Check if image is provided and allowed
                if file and allowed_file(file.filename):
                    image_data = file.read()
                    image_mimetype = file.mimetype

                # Create new product entry
                new_product = SaleProduct(
                    name=name,
                    description=description,
                    price=price,
                    quantity=quantity,
                    image_data=image_data,
                    image_mimetype=image_mimetype
                )

                db.session.add(new_product)
                db.session.commit()

                flash('Product added successfully!', 'success')
                return redirect(url_for('sale'))

            except ValueError:
                flash('Invalid price or quantity.', 'danger')
            except Exception as e:
                flash(f'An error occurred: {e}', 'danger')

        return render_template('add_product_sale.html')

    else:
        flash('You need to log in first.', 'warning')
        return redirect(url_for('login'))

@app.route('/product-sale-image/<int:product_id>')
def product_sale_image(product_id):
    product = SaleProduct.query.get_or_404(product_id)
    if not product.image_data:
        return 'No image', 404
    return send_file(
        io.BytesIO(product.image_data),
        mimetype=product.image_mimetype,
        download_name=f"product_{product.id}.jpg"
    )

@app.route('/edit-product-sale/<int:product_id>', methods=['GET', 'POST'])
def edit_product_sale(product_id):
    product = SaleProduct.query.get_or_404(product_id)

    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.price = float(request.form['price'])
        product.quantity = int(request.form['quantity'])

        # Handle image update (optional)
        image_file = request.files.get('image')
        if image_file and image_file.filename:
            product.image_data = image_file.read()
            product.image_mimetype = image_file.mimetype

        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('sale'))

    return render_template('edit_product_sale.html', product=product)


@app.route('/delete-sale-product/<int:product_id>', methods=['POST'])
def delete_sale_product(product_id):
    if 'username' in session:
        product = SaleProduct.query.get(product_id)
        if product:
            db.session.delete(product)
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Product not found'}), 404
    return jsonify({'success': False, 'error': 'Unauthorized'}), 401

@app.route('/purchased-products')
def purchased_products():
    if 'username' in session:
        products = PurchasedProduct.query.all()
        return jsonify([
            {
                'id': p.id,
                'name': p.name,
                'quantity': p.quantity,
                'status': p.status,
                'username': p.username
            } for p in products
        ])
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/update-delivery-status/<int:product_id>', methods=['POST'])
def update_delivery_status(product_id):
    product = PurchasedProduct.query.get_or_404(product_id)
    new_status = request.json.get('status')
    if new_status in ["Pending", "Delivered"]:
        product.status = new_status
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Invalid status'}), 400

@app.route('/book-gift', methods=['GET', 'POST'])
def book_gift():
    if request.method == 'POST':
        gift_name = request.form.get('gift_name')  # <-- New line
        image = request.files.get('image')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        amount = int(request.form.get('amount'))

        image_data = image.read() if image else None
        mimetype = image.mimetype if image else None

        gift = GiftBooking(
            gift_name=gift_name,  # <-- Include in object
            image_data=image_data,
            image_mimetype=mimetype,
            description=description,
            price=price,
            amount=amount
        )
        db.session.add(gift)
        db.session.commit()
        flash("Gift successfully booked!", "success")
        return redirect(url_for('book_gift'))

    # 🟡 This line was missing
    gifts = GiftBooking.query.all()

    return render_template('book_gift.html', gifts=gifts)


@app.route('/gift-image/<int:gift_id>')
def gift_image(gift_id):
    gift = GiftBooking.query.get_or_404(gift_id)
    if gift.image_data:
        return Response(gift.image_data, mimetype=gift.image_mimetype)
    return "No image found", 404

@app.route('/add-gift', methods=['GET', 'POST'])
def add_gift():
    if request.method == 'POST':
        file = request.files.get('image')
        gift_name = request.form.get('gift_name')  # <-- NEW

        # Image handling
        if file and file.filename != '':
            image_data = file.read()
            mimetype = file.mimetype
        else:
            image_data = None
            mimetype = None

        try:
            price = abs(float(request.form['price']))
            amount = abs(int(request.form['amount']))
        except ValueError:
            return "Invalid input: price must be a number and amount must be an integer.", 400

        new_gift = GiftBooking(
            gift_name=gift_name,  # <-- NEW
            image_data=image_data,
            image_mimetype=mimetype,
            description=request.form['description'],
            price=price,
            amount=amount
        )
        db.session.add(new_gift)
        db.session.commit()
        return redirect(url_for('book_gift'))

    return render_template('add_gift.html')

@app.route('/edit-gift/<int:gift_id>', methods=['GET', 'POST'])
def edit_gift(gift_id):
    gift = GiftBooking.query.get_or_404(gift_id)

    if request.method == 'POST':
        gift.gift_name = request.form.get('gift_name')  # <-- NEW
        gift.description = request.form.get('description')
        try:
            gift.price = abs(float(request.form.get('price')))
            gift.amount = abs(int(request.form.get('amount')))
        except ValueError:
            flash("Invalid input.", "danger")
            return redirect(url_for('edit_gift', gift_id=gift_id))

        image = request.files.get('image')
        if image and image.filename != '':
            gift.image_data = image.read()
            gift.image_mimetype = image.mimetype

        db.session.commit()
        flash("Gift successfully updated!", "success")
        return redirect(url_for('book_gift'))

    return render_template('edit_gift.html', gift=gift)

@app.route('/increase-gift/<int:gift_id>', methods=['POST'])
def increase_gift(gift_id):
    gift = GiftBooking.query.get_or_404(gift_id)
    data = request.get_json()

    try:
        increase_amount = int(data.get('amount'))
        if increase_amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify(success=False), 400

    gift.amount += increase_amount
    db.session.commit()

    return jsonify(success=True, new_amount=gift.amount)

@app.route('/delete-gift/<int:gift_id>', methods=['POST'])
def delete_gift(gift_id):
    gift = GiftBooking.query.get_or_404(gift_id)
    db.session.delete(gift)
    db.session.commit()
    return jsonify(success=True)

@app.route('/get-booked-data')
def get_booked_data():
    booked_items = Booked.query.all()
    result = [{
        'id': b.id,
        'gift_name': b.gift_name,  # ✅ Add this line
        'description': b.description,
        'price': b.price,
        'quantity': b.quantity,
        'datetime': b.datetime.strftime("%Y-%m-%d %H:%M"),
        'customer_name': b.customer_name,
        'status': b.status
    } for b in booked_items]
    return jsonify(result)

@app.route('/update-booked-status/<int:booked_id>', methods=['POST'])
def update_booked_status(booked_id):
    data = request.get_json()
    new_status = data.get('status')
    booked_item = Booked.query.get(booked_id)
    if booked_item:
        booked_item.status = new_status
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/buy-stock')
def buy_stock():
    stocks = Stock.query.all()
    return render_template('buy_stock.html', stocks=stocks)

@app.route('/stock-image/<int:stock_id>')
def stock_image(stock_id):
    stock_item = Stock.query.get_or_404(stock_id)
    if stock_item.image_data:
        return Response(stock_item.image_data, mimetype=stock_item.image_mimetype)
    return '', 404

@app.route('/add-stock', methods=['GET', 'POST'])
def add_stock():
    if request.method == 'POST':
        product_name = request.form['product_name']
        description = request.form['description']
        price = float(request.form['price'])
        image_file = request.files['image']
        image_data = image_file.read() if image_file else None
        mimetype = image_file.mimetype if image_file else None

        new_product = Stock(
            product_name=product_name,
            description=description,
            price=price,
            image_data=image_data,
            image_mimetype=mimetype,
            quantity=0  # Default or set from form if needed
        )
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for('buy_stock'))

    return render_template('add_stock.html')

@app.template_filter('b64encode')
def b64encode_filter(data):
    return Markup(base64.b64encode(data).decode('utf-8')) if data else ''

@app.route('/buy-stock/<int:product_id>', methods=['POST'])
def buy_stock_action(product_id):
    stock = Stock.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 0))

    if quantity <= 0:
        return jsonify({'status': 'error', 'message': 'Quantity must be more than 0'})

    stock.quantity -= quantity

    purchase = BuyStock(
        product_name=stock.product_name,
        description=stock.description,
        price=stock.price,
        quantity=quantity
    )
    db.session.add(purchase)
    db.session.commit()
    return jsonify({'status': 'success'})



@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(host="0.0.0.0", port=5001, debug=True)
