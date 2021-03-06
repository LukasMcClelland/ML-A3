# -*- coding: utf-8 -*-
"""a3_CNN.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/113ZhEGdxAfO72Eug-g6Kgu_PBvqwzeNl
"""

from google.colab import drive
drive.mount('/content/gdrive' )

import torch
if torch.cuda.is_available():
    print("Running on GPU")
    device = torch.device("cuda")
else:
    print("Running on CPU")
    device = torch.device("cpu")
torch.set_default_tensor_type('torch.cuda.FloatTensor')

import pickle
import matplotlib.pyplot as plt
import numpy as np
from torchvision import transforms
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
from PIL import Image
from itertools import product
import time
import random
from keras.utils import np_utils

# Global variables
loadModelFromFile = False
produceSubmissionFile = False
modelFileName = './model.pth'

# Image transformation composition
img_transform = transforms.Compose([
    transforms.RandomHorizontalFlip(0.5),
    transforms.ToTensor(),
    transforms.Normalize([0.5], [0.5])
    
])

# Adapted dataset class to ease creationg of training, validation, and test sets
class MyBetterDataset(Dataset):
    def __init__(self, images, labels, transform=None):
        self.data = images
        self.targets = labels
        self.transform = transform

    def __len__(self):
        return len(self.targets)

    def __getitem__(self, index):
        img, target = self.data[index], int(self.targets[index])
        img = Image.fromarray(img.astype('uint8'), mode='L')

        if self.transform is not None:
           img = self.transform(img)

        return img, target

# The convNN used for this project
class MyConvNN(nn.Module):
    def __init__(self):
        super(MyConvNN, self).__init__()

        # SequentialLayer1
        self.layer1 = nn.Sequential(
            torch.nn.Conv2d(1, 32, kernel_size=5, stride=1, padding=2),
            torch.nn.ReLU(),
            torch.nn.MaxPool2d(kernel_size=2, stride=2),
            torch.nn.Dropout(p=0.1))

        # SequentialLayer2
        self.layer2 = nn.Sequential(
            torch.nn.Conv2d(32, 64, kernel_size=5, stride=1, padding=2),
            torch.nn.ReLU(),
            torch.nn.MaxPool2d(kernel_size=2, stride=2),
            torch.nn.Dropout(p=0.1))

        # SequentialLayer3
        self.layer3 = torch.nn.Sequential(
            torch.nn.Conv2d(64, 128, kernel_size=5, stride=1, padding=2),
            torch.nn.ReLU(),
            torch.nn.MaxPool2d(kernel_size=2, stride=2),
            torch.nn.Dropout(p=0.1))
        
        # SequentialLayer4
        self.layer4 = torch.nn.Sequential(
            torch.nn.Conv2d(128, 256, kernel_size=5, stride=1, padding=2),
            torch.nn.ReLU(),
            torch.nn.MaxPool2d(kernel_size=2, stride=2),
            torch.nn.Dropout(p=0.1))

        # LinearLayer1
        self.fc1 = nn.Linear(256 * 4 * 8, 1000, bias=True)
        torch.nn.init.xavier_uniform_(self.fc1.weight)

        # LinearLayer2
        self.fc2 = nn.Linear(1000, 10, bias=True)
        torch.nn.init.xavier_uniform_(self.fc2.weight)

    # How the network should do a forward pass
    def forward(self, x):
        out = self.layer1(x)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = out.reshape(out.size(0), -1)
        out = self.fc1(out)
        out = self.fc2(out)
        return out

# Read image data and their labels
allTrainData = pickle.load( open('gdrive/My Drive/ML-A3/Train.pkl', 'rb' ), encoding='bytes')
allTrainLabels = np.genfromtxt('gdrive/My Drive/ML-A3/TrainLabels.csv', delimiter=',')

# Zip images and labels together
z = list(zip(allTrainData, allTrainLabels))

# Shuffle data,label tuples
random.shuffle(z)

# Seperate data and labels back into seperate data structures
allTrainData, allTrainLabels = zip(*z)

# Define batchSize constant
batchSize = 32 

# If we're making a submission file, only use small a small portion of training data for validation
# (a good model and good hyperparameters should already have been found)
if produceSubmissionFile:
    allTestData = pickle.load( open('gdrive/My Drive/ML-A3/Test.pkl', 'rb' ), encoding='bytes')
    testData = MyBetterDataset(allTestData, allTrainLabels[:10000], img_transform)
    testLoader = DataLoader(testData, batch_size=batchSize, shuffle=False)
    trainData = MyBetterDataset(allTrainData[:55000], allTrainLabels[:55000], img_transform)
    trainLoader = DataLoader(trainData, batch_size=batchSize, shuffle=True)
    validationData = MyBetterDataset(allTrainData[55000:], allTrainLabels[55000:], img_transform)
    validationLoader  = DataLoader(validationData, batch_size=batchSize, shuffle=True)
else:
    trainData = MyBetterDataset(allTrainData[10000:], allTrainLabels[10000:], img_transform)
    validationData = MyBetterDataset(allTrainData[5000:10000], allTrainLabels[5000:10000], img_transform)
    testData = MyBetterDataset(allTrainData[:5000],allTrainLabels[:5000], img_transform)

    trainLoader = DataLoader(trainData, batch_size=batchSize, shuffle=True)
    validationLoader  = DataLoader(validationData, batch_size=batchSize, shuffle=True)
    testLoader  = DataLoader(testData, batch_size=batchSize, shuffle=False)

# Label names
classes = ['T-shirt/top', 'Trouser', 'Pullover', 'Dress', 'Coat', 'Sandal', 'Shirt', 'Sneaker', 'Bag', 'Ankle boot']

# Initialize NN and load the saved one from file if applicable
net = MyConvNN()
if loadModelFromFile:
    net.load_state_dict(torch.load(modelFileName))
net.cuda()

# Set loss and optimizer functions
criterion = nn.CrossEntropyLoss(weight=None, size_average=None, ignore_index=-100, reduce=None, reduction='mean')
optimizer = optim.Adam(net.parameters(), lr=0.00035, betas=(0.9, 0.999), eps=1e-08, weight_decay=0, amsgrad=True)

# Number of epoch the NN will train for
num_epochs = 1

print("Start training")
print("Batch size:", batch_size)
for epoch in range(num_epochs):
    startTime = time.time()
    running_loss = 0.0
    for i, data in enumerate(trainLoader):
        inputs, labels = data

        # Some optimizers/criterions need things to be in the one-hot format
        # Use "onehots" in liu of "labels"
        onehots = np_utils.to_categorical(labels.cpu(), 10)
        onehots = torch.from_numpy(onehots).cuda()

        # Set the parameter gradients to 0
        optimizer.zero_grad()

        # Feed forward
        outputs = net(inputs.cuda())
        loss = criterion(outputs, labels)

        # Backwards
        loss.backward()

        # Run optimizer
        optimizer.step()

        # Show some (potentially wildly inaccurate) info
        running_loss += loss.item()
        if i % 200 == 199:
            print("[", epoch + 1, ",", i + 1, "] loss:", running_loss / 200)
            running_loss = 0.0
        
    # End of epoch info
    print("End of Epoch", epoch + 1, ". Epoch time:", time.time() - startTime, "Loss:", loss.item())

    # Show acc on validation set at end of epoch
    correct = 0
    total = 0
    with torch.no_grad():
        for data in validationLoader:
            images, labels = data
            outputs = net(images.cuda())
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    print('Accuracy of the network on the 10000 validation images: %d %%' % (100 * correct / total))
    
    # Save the model after each epoch in case of interuption
    torch.save(net.state_dict(), modelFileName)
print('Training completed')

#Predict test set
correct = 0
total = 0
preds = []
timeO = time.time()
with torch.no_grad():
    for data in testLoader:
        images, labels = data
        outputs = net(images.cuda())
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        if not produceSubmissionFile:
            correct += (predicted == labels).sum().item()
        for p in predicted:
            preds.append(p)
print("Time to classify: ", time.time() - timeO)

if not produceSubmissionFile:
    # Print out test set accuracy if we're not making a file for submission
    print('Accuracy of the network on the 10000 test images: %d %%' % (100 * correct / total))
    # Sanity check
    rightOnes = 0
    for i in range(len(preds)):
        if preds[i] == testData.targets[i]:
            rightOnes += 1
    print(rightOnes / len(preds))

else:
    # Write predictions to file if we're making a submission file
    from google.colab import files
    with open('submission.txt', 'w') as f:
        f.write('id,output\n')
        for x in range(len(preds)):
            f.write(str(x) + "," + str(preds[x].item()) + "\n")
    print("Predictions completed and saved to file 'submission.txt'.")