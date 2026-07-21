"""
Machine Learning Model Training Script for Phishing Detection (Production-Ready)
=================================================================================

This script implements a production-grade ML pipeline with:
1. SMOTE for class balancing
2. RandomForestClassifier optimized for phishing detection
3. Recall-focused evaluation (prioritizing catching phishing URLs)
4. Comprehensive metrics including confusion matrix and classification report

Target: Achieve ≥90% phishing recall to minimize false negatives
"""

import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, 
                            f1_score, confusion_matrix, classification_report)
from imblearn.over_sampling import SMOTE
import warnings
warnings.filterwarnings('ignore')


def create_sample_dataset():
    """
    Create a sample phishing dataset for demonstration.
    In production, replace this with actual Kaggle dataset loading.
    
    Returns:
        pd.DataFrame: Sample dataset with enhanced features and labels
    """
    print("Creating sample dataset...")
    print("NOTE: For production, download phishing dataset from Kaggle")
    print("Recommended: https://www.kaggle.com/datasets/shashwatwork/phishing-dataset-for-machine-learning\n")
    
    # Sample data structure (replace with actual dataset)
    np.random.seed(42)
    n_samples = 5000
    
    # Generate synthetic features for demonstration
    # Phishing URLs (label = 1) - intentionally create imbalance (40% phishing)
    n_phishing = int(n_samples * 0.4)
    n_legitimate = n_samples - n_phishing
    
    phishing_data = {
        'url_length': np.random.randint(50, 200, n_phishing),
        'num_dots': np.random.randint(3, 10, n_phishing),
        'num_hyphens': np.random.randint(2, 8, n_phishing),
        'num_underscores': np.random.randint(1, 5, n_phishing),
        'num_slashes': np.random.randint(3, 10, n_phishing),
        'num_questionmarks': np.random.randint(0, 3, n_phishing),
        'num_equals': np.random.randint(0, 5, n_phishing),
        'num_at': np.random.randint(0, 2, n_phishing),
        'num_ampersand': np.random.randint(0, 3, n_phishing),
        'num_exclamation': np.random.randint(0, 2, n_phishing),
        'num_tilde': np.random.randint(0, 2, n_phishing),
        'num_percent': np.random.randint(0, 5, n_phishing),
        'num_special_chars_total': np.random.randint(5, 20, n_phishing),
        'has_https': np.random.choice([0, 1], n_phishing, p=[0.6, 0.4]),
        'has_ip': np.random.choice([0, 1], n_phishing, p=[0.3, 0.7]),
        'subdomain_count': np.random.randint(2, 5, n_phishing),
        'domain_length': np.random.randint(15, 40, n_phishing),
        'path_length': np.random.randint(20, 100, n_phishing),
        'query_length': np.random.randint(0, 50, n_phishing),
        'special_char_ratio': np.random.uniform(0.1, 0.3, n_phishing),
        'url_entropy': np.random.uniform(3.5, 5.0, n_phishing),
        'digit_ratio': np.random.uniform(0.1, 0.3, n_phishing),
        'letter_ratio': np.random.uniform(0.5, 0.7, n_phishing),
        'uppercase_ratio': np.random.uniform(0.1, 0.4, n_phishing),
        'consecutive_consonants_max': np.random.randint(3, 8, n_phishing),
        'tld_suspicious': np.random.choice([0, 1], n_phishing, p=[0.5, 0.5]),
        'has_suspicious_words': np.random.choice([0, 1], n_phishing, p=[0.3, 0.7]),
        'domain_age_days': np.random.randint(0, 365, n_phishing),
        'registration_length_days': np.random.randint(30, 730, n_phishing),
        'privacy_protection_flag': np.random.choice([0, 1], n_phishing, p=[0.4, 0.6]),
        'registrar_reputation': np.random.choice([-1, 0, 1], n_phishing, p=[0.3, 0.5, 0.2]),
        'is_shortened': np.random.choice([0, 1], n_phishing, p=[0.7, 0.3]),
        'label': np.ones(n_phishing, dtype=int)
    }
    
    # Legitimate URLs (label = 0)
    legitimate_data = {
        'url_length': np.random.randint(20, 80, n_legitimate),
        'num_dots': np.random.randint(1, 4, n_legitimate),
        'num_hyphens': np.random.randint(0, 3, n_legitimate),
        'num_underscores': np.random.randint(0, 2, n_legitimate),
        'num_slashes': np.random.randint(2, 6, n_legitimate),
        'num_questionmarks': np.random.randint(0, 2, n_legitimate),
        'num_equals': np.random.randint(0, 3, n_legitimate),
        'num_at': np.random.randint(0, 1, n_legitimate),
        'num_ampersand': np.random.randint(0, 2, n_legitimate),
        'num_exclamation': np.random.randint(0, 1, n_legitimate),
        'num_tilde': np.random.randint(0, 1, n_legitimate),
        'num_percent': np.random.randint(0, 2, n_legitimate),
        'num_special_chars_total': np.random.randint(0, 8, n_legitimate),
        'has_https': np.random.choice([0, 1], n_legitimate, p=[0.2, 0.8]),
        'has_ip': np.random.choice([0, 1], n_legitimate, p=[0.95, 0.05]),
        'subdomain_count': np.random.randint(0, 2, n_legitimate),
        'domain_length': np.random.randint(5, 20, n_legitimate),
        'path_length': np.random.randint(0, 50, n_legitimate),
        'query_length': np.random.randint(0, 30, n_legitimate),
        'special_char_ratio': np.random.uniform(0.0, 0.1, n_legitimate),
        'url_entropy': np.random.uniform(2.0, 3.5, n_legitimate),
        'digit_ratio': np.random.uniform(0.0, 0.1, n_legitimate),
        'letter_ratio': np.random.uniform(0.7, 0.9, n_legitimate),
        'uppercase_ratio': np.random.uniform(0.0, 0.15, n_legitimate),
        'consecutive_consonants_max': np.random.randint(0, 4, n_legitimate),
        'tld_suspicious': np.random.choice([0, 1], n_legitimate, p=[0.9, 0.1]),
        'has_suspicious_words': np.random.choice([0, 1], n_legitimate, p=[0.9, 0.1]),
        'domain_age_days': np.random.randint(365, 5000, n_legitimate),
        'registration_length_days': np.random.randint(365, 3650, n_legitimate),
        'privacy_protection_flag': np.random.choice([0, 1], n_legitimate, p=[0.7, 0.3]),
        'registrar_reputation': np.random.choice([-1, 0, 1], n_legitimate, p=[0.1, 0.2, 0.7]),
        'is_shortened': np.random.choice([0, 1], n_legitimate, p=[0.95, 0.05]),
        'label': np.zeros(n_legitimate, dtype=int)
    }
    
    # Combine datasets
    df_phishing = pd.DataFrame(phishing_data)
    df_legitimate = pd.DataFrame(legitimate_data)
    df = pd.concat([df_phishing, df_legitimate], ignore_index=True)
    
    # Shuffle the dataset
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    print(f"Dataset created: {len(df)} samples")
    print(f"Phishing URLs: {sum(df['label'] == 1)} ({sum(df['label'] == 1)/len(df)*100:.1f}%)")
    print(f"Legitimate URLs: {sum(df['label'] == 0)} ({sum(df['label'] == 0)/len(df)*100:.1f}%)")
    print(f"Class Imbalance Ratio: {sum(df['label'] == 0)/sum(df['label'] == 1):.2f}:1\n")
    
    return df


def load_dataset(filepath=None):
    """
    Load phishing dataset from CSV file.
    
    Args:
        filepath (str): Path to dataset CSV file
        
    Returns:
        pd.DataFrame: Loaded dataset
    """
    if filepath:
        try:
            df = pd.read_csv(filepath)
            print(f"Dataset loaded from {filepath}")
            return df
        except Exception as e:
            print(f"Error loading dataset: {e}")
            print("Using sample dataset instead...\n")
    
    return create_sample_dataset()


def preprocess_data(df):
    """
    Clean and preprocess the dataset.
    
    Args:
        df (pd.DataFrame): Raw dataset
        
    Returns:
        tuple: (X, y) features and labels
    """
    print("Preprocessing data...")
    
    # Handle missing values
    df = df.fillna(df.median(numeric_only=True))
    
    # Separate features and labels
    X = df.drop('label', axis=1)
    y = df['label']
    
    print(f"Features shape: {X.shape}")
    print(f"Labels shape: {y.shape}")
    print(f"Number of features: {X.shape[1]}\n")
    
    return X, y


def apply_smote(X_train, y_train):
    """
    Apply SMOTE (Synthetic Minority Over-sampling Technique) to balance the dataset.
    
    Args:
        X_train: Training features
        y_train: Training labels
        
    Returns:
        tuple: (X_resampled, y_resampled) balanced training data
    """
    print("=" * 80)
    print("APPLYING SMOTE FOR CLASS BALANCING")
    print("=" * 80)
    
    # Count original class distribution
    unique, counts = np.unique(y_train, return_counts=True)
    print(f"\nOriginal training set distribution:")
    print(f"  Legitimate (0): {counts[0]} samples")
    print(f"  Phishing (1): {counts[1]} samples")
    print(f"  Imbalance ratio: {counts[0]/counts[1]:.2f}:1")
    
    # Apply SMOTE
    smote = SMOTE(random_state=42, k_neighbors=5)
    X_resampled, y_resampled = smote.fit_resample(X_train, y_train)
    
    # Count new class distribution
    unique, counts = np.unique(y_resampled, return_counts=True)
    print(f"\nAfter SMOTE:")
    print(f"  Legitimate (0): {counts[0]} samples")
    print(f"  Phishing (1): {counts[1]} samples")
    print(f"  Balance ratio: {counts[0]/counts[1]:.2f}:1")
    print(f"  Total training samples: {len(X_resampled)} (increased from {len(X_train)})")
    print("=" * 80 + "\n")
    
    return X_resampled, y_resampled


def train_and_evaluate_models(X_train, X_test, y_train, y_test):
    """
    Train and compare multiple ML models with RECALL-FOCUSED evaluation.
    
    Args:
        X_train, X_test: Training and testing features
        y_train, y_test: Training and testing labels
        
    Returns:
        dict: Dictionary containing trained models and their metrics
    """
    print("=" * 80)
    print("TRAINING AND EVALUATING MODELS (RECALL-FOCUSED)")
    print("=" * 80)
    
    # Dictionary to store results
    results = {}
    
    # Model 1: Logistic Regression (baseline)
    print("\n1. Training Logistic Regression (Baseline)...")
    lr_model = LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced')
    lr_model.fit(X_train, y_train)
    lr_pred = lr_model.predict(X_test)
    
    results['Logistic Regression'] = {
        'model': lr_model,
        'predictions': lr_pred,
        'accuracy': accuracy_score(y_test, lr_pred),
        'precision': precision_score(y_test, lr_pred, zero_division=0),
        'recall': recall_score(y_test, lr_pred, zero_division=0),
        'phishing_recall': recall_score(y_test, lr_pred, pos_label=1, zero_division=0),
        'f1_score': f1_score(y_test, lr_pred, zero_division=0)
    }
    
    # Model 2: Random Forest (PRIMARY MODEL - optimized for phishing detection)
    print("2. Training Random Forest Classifier (Primary Model)...")
    rf_model = RandomForestClassifier(
        n_estimators=300,           # Increased from 100
        class_weight='balanced',    # Handle any remaining imbalance
        max_depth=20,               # Prevent overfitting
        min_samples_split=10,       # Better generalization
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    rf_pred = rf_model.predict(X_test)
    
    results['Random Forest'] = {
        'model': rf_model,
        'predictions': rf_pred,
        'accuracy': accuracy_score(y_test, rf_pred),
        'precision': precision_score(y_test, rf_pred, zero_division=0),
        'recall': recall_score(y_test, rf_pred, zero_division=0),
        'phishing_recall': recall_score(y_test, rf_pred, pos_label=1, zero_division=0),
        'f1_score': f1_score(y_test, rf_pred, zero_division=0)
    }
    
    # Model 3: XGBoost (comparison)
    print("3. Training XGBoost Classifier (Comparison)...")
    xgb_model = XGBClassifier(
        n_estimators=200,
        random_state=42,
        use_label_encoder=False,
        eval_metric='logloss',
        scale_pos_weight=1  # Balanced by SMOTE
    )
    xgb_model.fit(X_train, y_train)
    xgb_pred = xgb_model.predict(X_test)
    
    results['XGBoost'] = {
        'model': xgb_model,
        'predictions': xgb_pred,
        'accuracy': accuracy_score(y_test, xgb_pred),
        'precision': precision_score(y_test, xgb_pred, zero_division=0),
        'recall': recall_score(y_test, xgb_pred, zero_division=0),
        'phishing_recall': recall_score(y_test, xgb_pred, pos_label=1, zero_division=0),
        'f1_score': f1_score(y_test, xgb_pred, zero_division=0)
    }
    
    return results


def display_results(results, y_test):
    """
    Display comprehensive results for all models with PHISHING RECALL as primary metric.
    
    Args:
        results (dict): Dictionary containing model results
        y_test: True labels
        
    Returns:
        str: Name of the best model (based on phishing recall)
    """
    print("\n" + "=" * 80)
    print("MODEL PERFORMANCE COMPARISON (SORTED BY PHISHING RECALL)")
    print("=" * 80)
    
    # Create comparison table
    comparison_df = pd.DataFrame({
        'Model': list(results.keys()),
        'Phishing Recall': [results[m]['phishing_recall'] for m in results],
        'Accuracy': [results[m]['accuracy'] for m in results],
        'Precision': [results[m]['precision'] for m in results],
        'Overall Recall': [results[m]['recall'] for m in results],
        'F1-Score': [results[m]['f1_score'] for m in results]
    })
    
    # Sort by phishing recall (descending)
    comparison_df = comparison_df.sort_values('Phishing Recall', ascending=False)
    
    print("\n" + comparison_df.to_string(index=False))
    
    # Find best model based on PHISHING RECALL
    best_model_name = comparison_df.iloc[0]['Model']
    best_phishing_recall = comparison_df.iloc[0]['Phishing Recall']
    
    print("\n" + "=" * 80)
    print(f"BEST MODEL: {best_model_name}")
    print(f"PHISHING RECALL: {best_phishing_recall:.4f} ({best_phishing_recall*100:.2f}%)")
    print("=" * 80)
    
    # Display detailed metrics for best model
    best_pred = results[best_model_name]['predictions']
    cm = confusion_matrix(y_test, best_pred)
    
    print(f"\nDetailed Metrics for {best_model_name}:")
    print("-" * 80)
    
    # Confusion Matrix breakdown
    tn, fp, fn, tp = cm.ravel()
    print("\nConfusion Matrix:")
    print(f"  True Negatives (TN):  {tn:4d} - Legitimate correctly identified")
    print(f"  False Positives (FP): {fp:4d} - Legitimate incorrectly flagged as phishing")
    print(f"  False Negatives (FN): {fn:4d} - ⚠️  PHISHING MISSED (Critical!)")
    print(f"  True Positives (TP):  {tp:4d} - Phishing correctly caught")
    
    # Calculate phishing-specific metrics
    phishing_precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    phishing_recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    false_negative_rate = fn / (tp + fn) if (tp + fn) > 0 else 0
    
    print(f"\nPhishing Detection Metrics:")
    print(f"  Phishing Precision: {phishing_precision:.4f} ({phishing_precision*100:.2f}%)")
    print(f"  Phishing Recall:    {phishing_recall:.4f} ({phishing_recall*100:.2f}%)")
    print(f"  False Negative Rate: {false_negative_rate:.4f} ({false_negative_rate*100:.2f}%)")
    
    # Check if target is met
    if phishing_recall >= 0.90:
        print(f"\n✅ TARGET MET: Phishing recall ≥ 90% ({phishing_recall*100:.2f}%)")
    else:
        print(f"\n⚠️  TARGET NOT MET: Phishing recall < 90% ({phishing_recall*100:.2f}%)")
        print("   Consider: Lower prediction threshold or collect more phishing samples")
    
    # Full classification report
    print("\nClassification Report:")
    print("-" * 80)
    print(classification_report(y_test, best_pred,
                               target_names=['Legitimate', 'Phishing'],
                               digits=4))
    
    return best_model_name


def plot_confusion_matrices(results, y_test):
    """
    Plot confusion matrices for all models.
    
    Args:
        results (dict): Dictionary containing model results
        y_test: True labels
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    
    for idx, (model_name, model_data) in enumerate(results.items()):
        cm = confusion_matrix(y_test, model_data['predictions'])
        
        # Calculate phishing recall for title
        phishing_recall = model_data['phishing_recall']
        
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[idx],
                   xticklabels=['Legitimate', 'Phishing'],
                   yticklabels=['Legitimate', 'Phishing'])
        
        axes[idx].set_title(f'{model_name}\nPhishing Recall: {phishing_recall:.4f}')
        axes[idx].set_ylabel('True Label')
        axes[idx].set_xlabel('Predicted Label')
    
    plt.tight_layout()
    plt.savefig('model/confusion_matrices.png', dpi=300, bbox_inches='tight')
    print("\nConfusion matrices saved to: model/confusion_matrices.png")
    plt.close()


def save_best_model(results, best_model_name, scaler):
    """
    Save the best performing model to disk.
    
    Args:
        results (dict): Dictionary containing model results
        best_model_name (str): Name of the best model
        scaler: Fitted scaler object
    """
    best_model = results[best_model_name]['model']
    
    # Save model
    joblib.dump(best_model, 'model/best_model.pkl')
    print(f"\nBest model ({best_model_name}) saved to: model/best_model.pkl")
    
    # Save scaler
    joblib.dump(scaler, 'model/scaler.pkl')
    print("Scaler saved to: model/scaler.pkl")
    
    # Save model metadata (including phishing recall)
    metadata = {
        'model_name': best_model_name,
        'accuracy': results[best_model_name]['accuracy'],
        'precision': results[best_model_name]['precision'],
        'recall': results[best_model_name]['recall'],
        'phishing_recall': results[best_model_name]['phishing_recall'],
        'f1_score': results[best_model_name]['f1_score']
    }
    
    joblib.dump(metadata, 'model/model_metadata.pkl')
    print("Model metadata saved to: model/model_metadata.pkl")


def main():
    """
    Main function to orchestrate the training pipeline.
    """
    print("\n" + "=" * 80)
    print("PHISHING DETECTION - PRODUCTION-READY MODEL TRAINING PIPELINE")
    print("=" * 80 + "\n")
    
    # Step 1: Load dataset
    # For production, use: df = load_dataset('dataset/phishing_urls.csv')
    df = load_dataset()
    
    # Step 2: Preprocess data
    X, y = preprocess_data(df)
    
    # Step 3: Split dataset (80% train, 20% test)
    print("Splitting dataset (80% train, 20% test)...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Training samples: {len(X_train)}")
    print(f"Testing samples: {len(X_test)}\n")
    
    # Step 4: Apply SMOTE to balance training data
    X_train_balanced, y_train_balanced = apply_smote(X_train, y_train)
    
    # Step 5: Feature scaling
    print("Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_balanced)
    X_test_scaled = scaler.transform(X_test)
    print("Feature scaling completed.\n")
    
    # Step 6: Train and evaluate models
    results = train_and_evaluate_models(X_train_scaled, X_test_scaled, 
                                       y_train_balanced, y_test)
    
    # Step 7: Display results (sorted by phishing recall)
    best_model_name = display_results(results, y_test)
    
    # Step 8: Plot confusion matrices
    plot_confusion_matrices(results, y_test)
    
    # Step 9: Save best model
    save_best_model(results, best_model_name, scaler)
    
    print("\n" + "=" * 80)
    print("TRAINING COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. Review the confusion matrices in model/confusion_matrices.png")
    print("2. Check phishing recall - should be ≥ 90%")
    print("3. Update app.py to use probability-based predictions")
    print("4. Run the Flask app with: python app.py")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
