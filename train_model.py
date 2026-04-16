# ==========================================================================
# train_model_fixed.py
# ==========================================================================
# Fixed for latest wfdb version (uses pn_dir instead of pb_dir)
# ==========================================================================

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import os

def download_and_preprocess_mit_bih():
    """Download MIT-BIH Arrhythmia Database and extract features."""
    try:
        import wfdb
    except ImportError:
        print("wfdb not installed. Run: pip install wfdb")
        return None, None
    
    # Records to use
    records = ['100', '101', '102', '103', '104', '105', '106', '107', '108', '109',
               '111', '112', '113', '114', '115', '116', '117', '118', '119', '121',
               '122', '123', '124', '200', '201', '202', '203', '205', '207', '208',
               '209', '210', '212', '213', '214', '215', '217', '219', '220', '221',
               '222', '223', '228', '230', '231', '232', '233', '234']
    
    X_list = []
    y_list = []
    
    for rec in records:
        try:
            # Load record - using pn_dir (new API) instead of pb_dir (old API)
            record = wfdb.rdrecord(rec, pn_dir='mitdb')
            annotation = wfdb.rdann(rec, 'atr', pn_dir='mitdb')
            signal = record.p_signal[:, 0]  # Lead II
            fs = record.fs
            
            # Simple R-peak detection using thresholding
            # Normalize signal
            signal_norm = (signal - np.mean(signal)) / np.std(signal)
            
            # Find peaks (simple threshold crossing)
            threshold = 1.5
            r_peaks = []
            for i in range(1, len(signal_norm)-1):
                if signal_norm[i] > threshold and signal_norm[i] > signal_norm[i-1] and signal_norm[i] > signal_norm[i+1]:
                    r_peaks.append(i)
            
            if len(r_peaks) > 3:
                # Calculate RR intervals in seconds
                rr_intervals = np.diff(r_peaks) / fs
                # Heart Rate = 60 / average RR interval
                heart_rate = 60 / np.mean(rr_intervals)
                # HRV = standard deviation of RR intervals (in ms)
                hrv = np.std(rr_intervals) * 1000
            else:
                # Fallback values
                heart_rate = 75
                hrv = 40
            
            # SpO2 is not in MIT-BIH - use realistic placeholder based on health
            # In real system, this comes from your MAX30102 sensor
            spo2 = np.random.normal(97, 2)
            
            # Motion energy - not in MIT-BIH (ECG is resting)
            motion_energy = np.random.uniform(0.5, 2.0)
            
            # Determine if record contains abnormal beats
            # Normal beat symbols: N, L, R, e, j
            # Abnormal: V (PVC), S (Supraventricular), F (Fusion), Q (Unclassifiable), f (Fusion)
            abnormal_symbols = ['V', 'S', 'F', 'Q', 'f', '[' , '!', ']', 'x']
            
            # Check annotation symbols
            ann_symbols = annotation.symbol
            is_abnormal = any(sym in abnormal_symbols for sym in ann_symbols)
            label = 1 if is_abnormal else 0
            
            X_list.append([heart_rate, spo2, hrv, motion_energy])
            y_list.append(label)
            
            status = "ABNORMAL" if is_abnormal else "normal"
            print(f"✓ {rec}: HR={heart_rate:.0f}bpm, HRV={hrv:.1f}ms, {status}")
            
        except Exception as e:
            print(f"✗ Failed to process {rec}: {e}")
    
    if len(X_list) == 0:
        return None, None
    
    X = np.array(X_list)
    y = np.array(y_list)
    
    print(f"\nTotal samples: {len(X)}")
    print(f"Normal (0): {sum(y==0)}")
    print(f"Abnormal (1): {sum(y==1)}")
    
    return X, y

def generate_synthetic_data():
    """Generate synthetic training data as fallback."""
    print("\nGenerating synthetic training data...")
    
    # Normal samples (label=0)
    normal_hr = np.random.uniform(60, 100, 1000)
    normal_spo2 = np.random.uniform(95, 100, 1000)
    normal_hrv = np.random.uniform(40, 80, 1000)
    normal_motion = np.random.uniform(0.5, 5, 1000)
    X_normal = np.column_stack([normal_hr, normal_spo2, normal_hrv, normal_motion])
    y_normal = np.zeros(1000)
    
    # Abnormal samples (label=1)
    abnormal_hr = np.random.uniform(110, 160, 1000)
    abnormal_spo2 = np.random.uniform(85, 93, 1000)
    abnormal_hrv = np.random.uniform(10, 35, 1000)
    abnormal_motion = np.random.uniform(8, 30, 1000)
    X_abnormal = np.column_stack([abnormal_hr, abnormal_spo2, abnormal_hrv, abnormal_motion])
    y_abnormal = np.ones(1000)
    
    X = np.vstack([X_normal, X_abnormal])
    y = np.concatenate([y_normal, y_abnormal])
    
    print(f"Generated {len(X)} synthetic samples")
    
    return X, y

def train_model():
    print("CardioSentinel Model Training")
    print("=============================")
    
    # Try MIT-BIH first
    X, y = download_and_preprocess_mit_bih()
    
    # Fallback to synthetic if MIT-BIH fails
    if X is None or len(X) < 20:
        print("\nMIT-BIH download failed or insufficient data.")
        print("Falling back to synthetic data...")
        X, y = generate_synthetic_data()
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Train model (optimized for edge deployment)
    print("\nTraining Random Forest Classifier...")
    model = RandomForestClassifier(
        n_estimators=50,      # Fewer trees = faster inference
        max_depth=5,          # Limited depth prevents overfitting
        random_state=42,
        n_jobs=-1             # Use all CPU cores
    )
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    print("\n=== Model Performance ===")
    print(classification_report(y_test, y_pred, target_names=['Normal', 'Abnormal']))
    
    # Feature importance
    print("\n=== Feature Importance ===")
    features = ['Heart Rate (bpm)', 'SpO2 (%)', 'HRV (ms)', 'Motion Energy (m/s²)']
    for name, importance in zip(features, model.feature_importances_):
        print(f"  {name}: {importance:.3f}")
    
    # Save model
    joblib.dump(model, 'trained_model.pkl')
    print("\n✓ Model saved to 'trained_model.pkl'")
    print(f"  Expected input features: {model.n_features_in_}")
    print(f"  Output classes: {model.classes_} (0=Normal, 1=Abnormal)")

if __name__ == "__main__":
    train_model()