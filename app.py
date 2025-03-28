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
    type = db.Column(db.String(50), nullable=True)  # Now allows NULL and defaults to "Uncategorized"
    description = db.Column(db.String(500), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    priority = db.Column(db.String(10), nullable=False, default='Low')
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

@app.route('/inventory')
def inventory():
    if 'username' in session:
        # Fetch products sorted by type and priority
        products = Product.query.order_by(
            db.func.ifnull(Product.type, "Uncategorized"),  # Handle NULL types
            db.case(
                (Product.priority == 'High', 1),
                (Product.priority == 'Medium', 2),
                (Product.priority == 'Low', 3)
            ),
            Product.name.asc()
        ).all()

        # Group products by type, defaulting empty types to "Uncategorized"
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
            name = request.form['name']
            type = request.form.get('type', 'Uncategorized')  # Default to "Uncategorized"
            description = request.form.get('description', '')
            quantity = request.form['quantity']
            priority = request.form.get('priority', 'Low')
            file = request.files.get('image')

            try:
                quantity = int(quantity)
                image_filename = None
                if file and allowed_file(file.filename):
                    image_filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

                new_product = Product(
                    name=name,
                    type=type,
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
                flash('Invalid quantity.', 'danger')
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
            db.session.delete(product)
            db.session.commit()
            flash('Product deleted successfully!', 'success')
        else:
            flash('Product not found.', 'danger')
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
