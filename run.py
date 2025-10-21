#!/usr/bin/env python3
"""
Development server runner for Daily Job Search
"""

import os
from app import app, db

if __name__ == '__main__':
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Run the development server
    app.run(
        debug=True,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000))
    )
