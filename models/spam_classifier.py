import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import os
import config
from utils.text_processing import preprocess_text

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

def train_and_save_model():
    """Train the spam detection model"""
    print("Training spam detection model...")

    messages = [
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
        'Hey, are we meeting tomorrow?',
        'Can you pick up milk?',
        'Meeting at 3 PM conference room',
        'Thanks for your help yesterday',
        'What time is the movie?',
        'Good morning! Have a nice day',
        'Can I borrow your notes?',
        'See you at the meeting'
    ]

    labels = [1]*12 + [0]*8

    cleaned = [preprocess_text(msg) for msg in messages]
    vectorizer = TfidfVectorizer(max_features=config.MODEL_INPUT_SIZE, min_df=1, ngram_range=(1, 2))
    X = vectorizer.fit_transform(cleaned).toarray()

    X_tensor = torch.FloatTensor(X).to(device)
    y_tensor = torch.FloatTensor(labels).to(device)

    input_size = X.shape[1]
    model = SpamClassifier(input_size).to(device)
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=config.LEARNING_RATE)

    for epoch in range(config.TRAINING_EPOCHS):
        model.train()
        optimizer.zero_grad()
        outputs = model(X_tensor).squeeze()
        loss = criterion(outputs, y_tensor)
        loss.backward()
        optimizer.step()

        if (epoch + 1) % 50 == 0:
            print(f'Epoch [{epoch+1}/{config.TRAINING_EPOCHS}], Loss: {loss.item():.4f}')

    model.eval()
    with torch.no_grad():
        predictions = (model(X_tensor).squeeze() > 0.5).float()
        accuracy = (predictions == y_tensor).float().mean().item() * 100
        print(f'Training Accuracy: {accuracy:.2f}%')

    torch.save({
        'model_state_dict': model.state_dict(),
        'input_size': input_size
    }, config.MODEL_PATH)

    with open(config.VECTORIZER_PATH, 'wb') as f:
        pickle.dump(vectorizer, f)

    print("✓ Model saved!")
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
        
        