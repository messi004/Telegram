import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split # For data splitting[citation:2][citation:5]
import pandas as pd
import pickle
import os
import config
from utils.text_processing import preprocess_text
# For loading UCI dataset easily[citation:9]
from ucimlrepo import fetch_ucirepo

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

class SpamClassifier(nn.Module):
    """Neural Network for Spam Detection"""
    def __init__(self, input_size):
        super(SpamClassifier, self).__init__()
        self.fc1 = nn.Linear(input_size, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 1)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.3)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.sigmoid(self.fc3(x))
        return x

def load_and_combine_datasets():
    """
    Loads multiple public spam/ham datasets and combines them into a single DataFrame.
    Returns:
        pandas.DataFrame: Combined dataset with 'message' and 'label' columns.
    """
    all_data = []

    # --- 1. Load SMS Spam Collection from UCI (Highly Recommended)[citation:1][citation:9] ---
    try:
        print("Loading SMS Spam Collection dataset from UCI...")
        # Fetch the dataset using its ID[citation:9]
        sms_spam = fetch_ucirepo(id=228)
        # Get features (text) and targets (label)
        sms_df = pd.DataFrame({
            'message': sms_spam.data.features.iloc[:, 0],  # First column is the text
            'label': sms_spam.data.targets.iloc[:, 0]      # First column is the label
        })
        # The UCI dataset uses 'ham'/'spam' strings. Map to 0 and 1.
        sms_df['label'] = sms_df['label'].map({'ham': 0, 'spam': 1})
        all_data.append(sms_df)
        print(f"   Loaded {len(sms_df)} samples from UCI SMS dataset.")
    except Exception as e:
        print(f"   Could not load UCI dataset: {e}")

    # --- 2. Load Email Spam/Ham Dataset from opendatabay.com[citation:4] ---
    # You need to download the 'emails.csv' file first from the source.
    email_dataset_path = "emails.csv"  # <-- UPDATE THIS PATH
    try:
        if os.path.exists(email_dataset_path):
            print("Loading Email spam/ham dataset...")
            email_df = pd.read_csv(email_dataset_path, delimiter='\t')  # It's tab-delimited[citation:4]
            # Rename columns to match expected format: 'text' -> 'message', 'spam' -> 'label'
            email_df = email_df.rename(columns={'text': 'message', 'spam': 'label'})
            # Ensure label is integer (it should be 0/1 already)[citation:4]
            email_df['label'] = email_df['label'].astype(int)
            all_data.append(email_df[['message', 'label']])
            print(f"   Loaded {len(email_df)} samples from Email dataset.")
        else:
            print(f"   Email dataset not found at {email_dataset_path}. Skipping.")
    except Exception as e:
        print(f"   Could not load Email dataset: {e}")

    # --- (Optional) 3. Load SHED or other datasets ---
    # You can add more `try:` blocks here for other datasets like SHED[citation:6].

    # --- Combine all loaded data ---
    if not all_data:
        raise ValueError("Could not load any dataset. Please check sources and paths.")
    
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # --- 4. Add your original hard-coded examples (as a fallback/booster) ---
    original_messages = [
          'Congratulations! You won a free iPhone. Click here to claim now',
          'URGENT! Your account will be closed. Verify now immediately',
          'Win $1000 cash prize! Call now to claim your reward',
          'FREE entry to our exclusive lottery. Limited time offer',
          'Nude video call and sex chat available',
          'Service available contact me now',
          'Available for vc boys message me',
          'DM for special services',
          'Call girls available in your area',
          'Aunty bhabhi number lena hai dm karo',
          'Paisa kamao ghar baithe',
          'Ladki chahiye to message karo',
          'Your car warranty is about to expire! Call now',
          'You\'ve been selected for a free cruise vacation',
          'Bank alert: Suspicious activity detected on your account',
          'Limited time offer: 90% discount on all products',
          'Earn ₹50,000 per month working from home',
          'Your Netflix subscription has expired - update now',
          'Credit card approved! Zero interest for 6 months - apply now',
          'You have unclaimed tax refund of $852 - claim immediately',
          'Your Amazon account has been suspended - verify details',
          'Get instant loan without documents - approval guaranteed',
          'Your Facebook profile will be deleted in 24 hours',
          'Hot singles in your area waiting to meet you',
          'Your phone has been infected with virus - download cleaner',
          'Crypto investment opportunity - 300% returns guaranteed',
          'You won Samsung Galaxy S23 - claim within 2 hours',
          'WhatsApp gold version available - download free',
          'Microsoft tech support: Your computer has critical errors',
          'PayPal security alert - confirm your identity now',
          'Your Aadhar card needs update - click link to verify',
          'Ghar baithe paise kamaye - daily ₹5000 earning',
          'Shadi.com premium membership free for limited time',
          'Viagra tablets at 80% discount - discreet delivery',
          'Ladke/ladkiyon ke liye job opportunity - high salary',
          'Your PAN card is blocked - update KYC immediately',
          'Government scholarship money waiting for you - apply now',
          'Free recharge offer for Jio/Airtel users - click here',
          'Property deal in Delhi/Mumbai - 50% below market rate',
          'Ayurvedic medicine for height increase - guaranteed results',
          'Instagram verification badge available - pay ₹999',
          'Your OTP is 4839 - do not share with anyone',
          'Bitcoin investment scheme - double your money in 7 days',
          'Free grocery voucher worth ₹2000 - limited coupons',
          'You have 3 missed calls from this number - call back',
          'Job offer: Data entry work - ₹15,000 per month',
          'Your SIM card will be deactivated - re-verify now',
          'Matrimonial match: Perfect profile found for you'
    ]
    original_labels = [1]*12 + [0]*8
    original_df = pd.DataFrame({
        'message': original_messages,
        'label': original_labels
    })
    final_df = pd.concat([combined_df, original_df], ignore_index=True)
    
    print(f"Successfully combined {len(final_df)} total messages for training.")
    # Check class distribution
    print(f"   Class distribution - Ham (0): {(final_df['label'] == 0).sum()}, Spam (1): {(final_df['label'] == 1).sum()}")
    return final_df


def train_and_save_model():
    """Train the spam detection model using multiple data sources."""
    print("=== Training spam detection model with production data ===")
    
    # Step 1: Load data from multiple sources
    try:
        df = load_and_combine_datasets()
        messages = df['message'].tolist()
        labels = df['label'].tolist()
    except Exception as e:
        print(f"Fatal error loading datasets: {e}")
        print("Falling back to original hard-coded data.")
        # ... (revert to your original hard-coded messages and labels here)
        messages = ['Congratulations! You won...', ...]
        labels = [1, 1, ... 0, 0]

    # Step 2: Preprocess Text
    print("Preprocessing text...")
    cleaned = [preprocess_text(msg) for msg in messages]

    # Step 3: Split Data into Train and Validation Sets
    # This is CRUCIAL for evaluating real-world performance[citation:2][citation:5].
    print("Splitting data into training and validation sets...")
    # stratify ensures the spam/ham ratio is similar in both sets[citation:5].
    X_train, X_val, y_train, y_val = train_test_split(
        cleaned, labels, 
        test_size=0.2,           # Use 20% of data for validation
        random_state=42,         # For reproducible splits
        stratify=labels          # Maintains class balance in split[citation:5]
    )
    
    # Step 4: Vectorize Text (Fit only on training data)
    print("Creating TF-IDF features...")
    vectorizer = TfidfVectorizer(max_features=config.MODEL_INPUT_SIZE, min_df=1, ngram_range=(1, 2))
    X_train_vec = vectorizer.fit_transform(X_train).toarray()
    X_val_vec = vectorizer.transform(X_val).toarray()

    # Step 5: Convert to PyTorch Tensors
    X_train_tensor = torch.FloatTensor(X_train_vec).to(device)
    y_train_tensor = torch.FloatTensor(y_train).to(device)
    X_val_tensor = torch.FloatTensor(X_val_vec).to(device)
    y_val_tensor = torch.FloatTensor(y_val).to(device)

    input_size = X_train_vec.shape[1]
    print(f"Feature vector size: {input_size}")
    
    # Step 6: Initialize Model, Loss, Optimizer
    model = SpamClassifier(input_size).to(device)
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=config.LEARNING_RATE)

    # Step 7: Training Loop with Validation
    print(f"Starting training for {config.TRAINING_EPOCHS} epochs...")
    for epoch in range(config.TRAINING_EPOCHS):
        model.train()
        optimizer.zero_grad()
        # Forward pass on training data
        outputs = model(X_train_tensor).squeeze()
        loss = criterion(outputs, y_train_tensor)
        loss.backward()
        optimizer.step()

        # Evaluate on validation set every N epochs
        if (epoch + 1) % 50 == 0 or epoch == 0:
            model.eval()
            with torch.no_grad():
                # Training accuracy
                train_preds = (model(X_train_tensor).squeeze() > 0.5).float()
                train_acc = (train_preds == y_train_tensor).float().mean().item() * 100
                # Validation accuracy
                val_preds = (model(X_val_tensor).squeeze() > 0.5).float()
                val_acc = (val_preds == y_val_tensor).float().mean().item() * 100
                
            print(f'Epoch [{epoch+1:4d}/{config.TRAINING_EPOCHS}], '
                  f'Loss: {loss.item():.4f}, '
                  f'Train Acc: {train_acc:6.2f}%, '
                  f'Val Acc: {val_acc:6.2f}%')
            model.train()  # Set back to training mode

    # Step 8: Final Evaluation on Validation Set
    model.eval()
    with torch.no_grad():
        final_val_preds = (model(X_val_tensor).squeeze() > 0.5).float()
        final_val_acc = (final_val_preds == y_val_tensor).float().mean().item() * 100
        print(f'\n=== Training Complete ===')
        print(f'Final Validation Set Accuracy: {final_val_acc:.2f}%')

    # Step 9: Save Model and Vectorizer
    print("Saving model and vectorizer...")
    torch.save({
        'model_state_dict': model.state_dict(),
        'input_size': input_size
    }, config.MODEL_PATH)

    with open(config.VECTORIZER_PATH, 'wb') as f:
        pickle.dump(vectorizer, f)

    print("✓ Model trained and saved successfully!")
    return model, vectorizer

def load_spam_model():
    """Load pre-trained spam detection model"""
    try:
        if not os.path.exists(config.MODEL_PATH) or not os.path.exists(config.VECTORIZER_PATH):
            return train_and_save_model()

        with open(config.VECTORIZER_PATH, 'rb') as f:
            vectorizer = pickle.load(f)

        checkpoint = torch.load(config.MODEL_PATH, map_location=device)
        input_size = checkpoint['input_size']

        model = SpamClassifier(input_size).to(device)
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()

        print(f"✓ Model loaded! Input size: {input_size}")
        return model, vectorizer

    except Exception as e:
        print(f"Error loading model: {e}")
        return train_and_save_model()