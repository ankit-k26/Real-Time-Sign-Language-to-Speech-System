import os
import json
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential # type: ignore
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization # type: ignore
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau # type: ignore
from tensorflow.keras.optimizers import Adam # type: ignore

PROCESSED_DIR = "processed"
MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)

print("Loading data...")
X_train = np.load(os.path.join(PROCESSED_DIR, "X_train.npy"))
y_train = np.load(os.path.join(PROCESSED_DIR, "y_train.npy"))
X_test = np.load(os.path.join(PROCESSED_DIR, "X_test.npy"))
y_test = np.load(os.path.join(PROCESSED_DIR, "y_test.npy"))

with open(os.path.join(PROCESSED_DIR, "label_map.json"), "r") as f:
    label_map = json.load(f)

num_classes = len(label_map)
print(f"Num classes: {num_classes}")

model = Sequential([
    LSTM(64, return_sequences=True, input_shape=(30, 126),
         dropout=0.2, recurrent_dropout=0.2),
    BatchNormalization(),
    LSTM(64, return_sequences=False, dropout=0.2, recurrent_dropout=0.2),
    BatchNormalization(),
    Dense(64, activation='relu'),
    Dropout(0.3),
    Dense(32, activation='relu'),
    Dropout(0.2),
    Dense(num_classes, activation='softmax'),
], name='SignLanguageLSTM')

model.compile(
    optimizer=Adam(1e-3),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

callbacks = [
    EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True, verbose=1),
    ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-6, verbose=1),
]

print("Training...")
model.fit(
    X_train, y_train,
    validation_data=(X_test, y_test),
    epochs=50,
    batch_size=16,
    callbacks=callbacks,
    verbose=1,
)

model_path = os.path.join(MODEL_DIR, "sign_model.h5")
model.save(model_path)
print(f"Saved to {model_path}")

meta_path = os.path.join(MODEL_DIR, "model_meta.json")
with open(meta_path, "w") as f:
    json.dump({"label_map": label_map}, f, indent=2)
print("Saved meta")
