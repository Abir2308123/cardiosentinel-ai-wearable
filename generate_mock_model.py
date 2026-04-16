# ==========================================================================
# generate_mock_model.py
# ==========================================================================
# UTILITY SCRIPT: Generates a mock Random Forest model for development
# and testing ONLY. In production, replace trained_model.pkl with your
# actual model trained on real clinical data (e.g., MIT-BIH Arrhythmia DB).
#
# The generated model matches the 4-feature schema expected by main.py:
#   [heart_rate (bpm), spo2 (%), hrv (ms), motion_energy (m/s²)]
# ==========================================================================

import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib

def create_mock_model():
    print("Generating dummy training data for CardioSentinel...")
    # Features: [Heart Rate (BPM), SpO2 (%), HRV (ms), Motion Energy (m/s²)]
    
    np.random.seed(42)
    
    # Normal data profile
    X_normal = np.column_stack((
        np.random.uniform(60, 100, 500),   # Heart Rate
        np.random.uniform(95, 100, 500),   # SpO2
        np.random.uniform(40, 80, 500),    # HRV
        np.random.uniform(0.5, 5.0, 500)   # Motion Energy (resting/walking)
    ))
    y_normal = np.zeros(500)  # 0 = Normal

    # Abnormal data profile
    X_abnormal = np.column_stack((
        np.random.uniform(110, 160, 500),  # Heart Rate (Tachycardia)
        np.random.uniform(85, 93, 500),    # SpO2 (Hypoxia)
        np.random.uniform(10, 35, 500),    # HRV (Very low)
        np.random.uniform(8.0, 30.0, 500)  # Motion Energy (fall/seizure)
    ))
    y_abnormal = np.ones(500)  # 1 = Abnormal

    X = np.vstack((X_normal, X_abnormal))
    y = np.concatenate((y_normal, y_abnormal))

    print("Training mock Random Forest Classifier (max_depth=5 for rapid inference)...")
    rf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    rf.fit(X, y)

    # Save as trained_model.pkl to match what main.py expects
    joblib.dump(rf, 'trained_model.pkl')
    print("Model saved to trained_model.pkl successfully.")
    print(f"  -> Expected features: {rf.n_features_in_}")
    print(f"  -> Classes: {rf.classes_}")

if __name__ == "__main__":
    create_mock_model()
