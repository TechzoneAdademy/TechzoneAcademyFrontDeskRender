#!/usr/bin/env python3
"""
Firebase Configuration for TechZone Academy Student Management System
"""

import firebase_admin
from firebase_admin import credentials, firestore, storage
import os
import json
from datetime import datetime

# Firebase Configuration
class FirebaseConfig:
    def __init__(self):
        self.db = None
        self.firebase_available = False
        self.initialize_firebase()
    
    def initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Path to your service account key file
            service_account_path = os.path.join(os.path.dirname(__file__), 'firebase-service-account.json')
            
            if not os.path.exists(service_account_path):
                print("❌ Firebase service account file not found!")
                print(f"Please place your firebase-service-account.json file in: {service_account_path}")
                print("Download it from Firebase Console → Project Settings → Service accounts")
                return
            
            # Read project ID from service account file
            with open(service_account_path, 'r') as f:
                service_account_info = json.load(f)
                project_id = service_account_info.get('project_id')
            
            # Initialize Firebase Admin SDK
            if not firebase_admin._apps:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred, {
                    'storageBucket': f'{project_id}.appspot.com'
                })
            
            # Get Firestore database
            self.db = firestore.client()
            
            # Get Firebase Storage bucket
            self.storage_bucket = storage.bucket()
            
            self.firebase_available = True
            print("Firebase Firestore connected successfully!")
            print("Firebase Storage connected successfully!")
            
        except Exception as e:
            print(f"Firebase initialization failed: {e}")
            print("Please check your firebase-service-account.json file")
            self.firebase_available = False
    
    def get_collection(self, collection_name):
        """Get a Firestore collection reference"""
        if not self.firebase_available:
            return None
        return self.db.collection(collection_name)
    
    def test_connection(self):
        """Test Firebase connection"""
        if not self.firebase_available:
            return False
        
        try:
            # Try to access a collection
            test_collection = self.db.collection('test')
            # This will create the collection if it doesn't exist
            test_doc = test_collection.document('connection_test')
            test_doc.set({
                'timestamp': datetime.now(),
                'message': 'Firebase connection test successful'
            })
            # Delete the test document
            test_doc.delete()
            print("✅ Firebase connection test passed!")
            return True
        except Exception as e:
            print(f"❌ Firebase connection test failed: {e}")
            return False

# Global Firebase instance
firebase_config = FirebaseConfig()
