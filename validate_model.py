# ==========================================================================
# validate_model.py - Quick utility to verify trained_model.pkl
# ==========================================================================
# Run this script to inspect whether your model file is compatible with
# CardioSentinel's 4-feature pipeline:
#   [heart_rate, spo2, hrv, motion_energy]
# ==========================================================================

import sys
import numpy as np

try:
    import joblib
except ImportError:
    print("ERROR: joblib not installed. Run: pip install joblib")
    sys.exit(1)

MODEL_PATH = 'trained_model.pkl'

print(f"Loading model from: {MODEL_PATH}")
try:
    model = joblib.load(MODEL_PATH)
except FileNotFoundError:
    print(f"FAIL: '{MODEL_PATH}' not found in project root.")
    sys.exit(1)

print(f"  Model type     : {type(model).__name__}")
print(f"  Expected inputs: {getattr(model, 'n_features_in_', 'unknown')}")
print(f"  Classes        : {getattr(model, 'classes_', 'unknown')}")

# Test with a sample healthy reading
sample_normal = np.array([[75.0, 98.0, 55.0, 2.5]])
# Test with a sample risky reading
sample_risky = np.array([[145.0, 88.0, 15.0, 22.0]])

try:
    pred_n = model.predict(sample_normal)[0]
    pred_r = model.predict(sample_risky)[0]
    print(f"\n  Test (Normal vitals)  -> Prediction: {int(pred_n)} ({'Normal' if pred_n == 0 else 'Abnormal'})")
    print(f"  Test (Risky vitals)   -> Prediction: {int(pred_r)} ({'Normal' if pred_r == 0 else 'Abnormal'})")

    if hasattr(model, 'predict_proba'):
        prob_n = model.predict_proba(sample_normal)[0]
        prob_r = model.predict_proba(sample_risky)[0]
        print(f"  Confidence (Normal)  : {max(prob_n)*100:.1f}%")
        print(f"  Confidence (Risky)   : {max(prob_r)*100:.1f}%")

    print("\n✅ Model validation PASSED. Compatible with CardioSentinel pipeline.")
except Exception as e:
    print(f"\n❌ Model validation FAILED: {e}")
    print("   Ensure the model expects exactly 4 features: [HR, SpO2, HRV, MotionEnergy]")
    sys.exit(1)
