#!/usr/bin/env python3
"""
Firebase Configuration for TechZone Academy Student Management System
Uses FIREBASE_CONFIG environment variable instead of a local JSON file.
"""

import firebase_admin
from firebase_admin import credentials, firestore, storage
import os
import json
from datetime import datetime
from dotenv import load_dotenv
import tempfile
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

# Load .env file locally (safe in dev)
if os.path.exists(".env"):
    load_dotenv()

class FirebaseConfig:
    def __init__(self):
        self.db = None
        self.storage_bucket = None
        self.firebase_available = False
        self.initialize_firebase()

    def initialize_firebase(self):
        """Initialize Firebase Admin SDK from environment variable via temp file"""
        temp_json_file = None
        try:
            firebase_config_str = os.getenv("FIREBASE_CONFIG")
            logging.debug(f"FIREBASE_CONFIG raw: {firebase_config_str}")

            if not firebase_config_str:
                logging.error("❌ FIREBASE_CONFIG environment variable not set!")
                return

            try:
                firebase_config = json.loads(firebase_config_str)
            except json.JSONDecodeError as e:
                logging.error(f"❌ Invalid FIREBASE_CONFIG JSON: {e}")
                return

            # Fix all forms of newlines in private_key
            if "private_key" in firebase_config:
                pk = firebase_config["private_key"]
                # Handle both '\\n' and '\n' (double-escaped and single-escaped)
                pk_fixed = pk.replace('\\n', '\n').replace('\r\n', '\n').replace('\r', '\n')
                firebase_config["private_key"] = pk_fixed
                logging.debug(f"private_key repr: {repr(pk_fixed)}")
                logging.debug(f"private_key length: {len(pk_fixed)}")
                logging.debug(f"private_key start: {pk_fixed[:40]}")
                logging.debug(f"private_key end: {pk_fixed[-40:]}")

            # Write the fixed config to a temp file
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as tf:
                json.dump(firebase_config, tf)
                temp_json_file = tf.name
                logging.debug(f"Wrote fixed FIREBASE_CONFIG to temp file: {temp_json_file}")

            if not firebase_admin._apps:
                cred = credentials.Certificate(temp_json_file)
                firebase_admin.initialize_app(cred, {
                    'storageBucket': firebase_config.get('project_id') + '.appspot.com'
                })

            self.db = firestore.client()
            self.storage_bucket = storage.bucket()
            self.firebase_available = True
            logging.info("✅ Firebase Firestore connected successfully!")
            logging.info("✅ Firebase Storage connected successfully!")
        except Exception as e:
            logging.error(f"❌ Firebase initialization failed: {e}")
            self.firebase_available = False
        finally:
            # Clean up temp file
            if temp_json_file and os.path.exists(temp_json_file):
                try:
                    os.remove(temp_json_file)
                    logging.debug(f"Deleted temp file: {temp_json_file}")
                except Exception as cleanup_err:
                    logging.warning(f"Could not delete temp file: {cleanup_err}")

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
            test_collection = self.db.collection('test')
            test_doc = test_collection.document('connection_test')
            test_doc.set({
                'timestamp': datetime.now(),
                'message': 'Firebase connection test successful'
            })
            test_doc.delete()
            logging.info("✅ Firebase connection test passed!")
            return True
        except Exception as e:
            logging.error(f"❌ Firebase connection test failed: {e}")
            return False

# Global Firebase instance
firebase_config = FirebaseConfig()
