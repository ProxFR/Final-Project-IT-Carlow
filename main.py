from flask import Blueprint, render_template
from flask_login import login_required, current_user
from .instances.main import drop
from . import db

instance_name = "First"
instance_region = "lon1"
instance_image = "debian-11-x64"
instance_size = "s-1vcpu-1gb"

drop1 = drop(instance_name, instance_region, instance_image, instance_size)

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', name=current_user.name)

@main.route('/create', methods=['POST'])
@login_required
def create():
    drop1.create()
    status = "Created"
    return render_template('testing.html', status=status)

@main.route('/destroy', methods=['POST'])
@login_required
def destroy():
    drop1.destroy()
    status = "Destroyed"
    return render_template('testing.html', status=status)