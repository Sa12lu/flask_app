import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Configuration (using XAMPP)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/flask_app'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# File Upload Configuration
UPLOAD_FOLDER = 'static/uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper function to check allowed file extensions
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
    description = db.Column(db.String(500), nullable=True)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    image_filename = db.Column(db.String(100), nullable=True)

# Initialize Database
with app.app_context():
    db.create_all()

# Routes
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
            flash('Invalid credentials. Please try again.', 'danger')
    
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

@app.route('/booking')
def booking():
    if 'username' in session:
        return render_template('booking.html')
    else:
        flash('You need to log in first.', 'warning')
        return redirect(url_for('login'))

@app.route('/inventory')
def inventory():
    if 'username' in session:
        products = Product.query.all()
        return render_template('inventory.html', products=products)
    else:
        flash('You need to log in first.', 'warning')
        return redirect(url_for('login'))

@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    if 'username' in session:
        if request.method == 'POST':
            name = request.form['name']
            description = request.form.get('description', '')
            price = request.form['price']
            quantity = request.form['quantity']
            file = request.files.get('image')

            try:
                # Validate input
                price = float(price)
                quantity = int(quantity)

                # Handle file upload
                image_filename = None
                if file and allowed_file(file.filename):
                    image_filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

                # Add product to database
                new_product = Product(
                    name=name,
                    description=description,
                    price=price,
                    quantity=quantity,
                    image_filename=image_filename
                )
                db.session.add(new_product)
                db.session.commit()

                flash('Product added successfully!', 'success')
                return redirect(url_for('inventory'))
            except ValueError:
                flash('Price and quantity must be valid numbers.', 'danger')
            except Exception as e:
                flash(f'An error occurred: {e}', 'danger')

        return render_template('add_product.html')
    else:
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
            name = request.form['name']
            description = request.form.get('description', '')
            price = request.form['price']
            quantity = request.form['quantity']
            file = request.files.get('image')

            try:
                # Validate input
                price = float(price)
                quantity = int(quantity)

                # Update product details
                product.name = name
                product.description = description
                product.price = price
                product.quantity = quantity

                if file and allowed_file(file.filename):
                    image_filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                    product.image_filename = image_filename

                db.session.commit()
                flash('Product updated successfully!', 'success')
                return redirect(url_for('inventory'))
            except ValueError:
                flash('Price and quantity must be valid numbers.', 'danger')
            except Exception as e:
                flash(f'An error occurred: {e}', 'danger')

        return render_template('edit_product.html', product=product)
    else:
        flash('You need to log in first.', 'warning')
        return redirect(url_for('login'))

@app.route('/delete-product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'username' in session:
        product = Product.query.get(product_id)
        if product:
            db.session.delete(product)
            db.session.commit()
            flash('Product deleted successfully.', 'success')
        else:
            flash('Product not found.', 'danger')
        return redirect(url_for('inventory'))
    else:
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

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
