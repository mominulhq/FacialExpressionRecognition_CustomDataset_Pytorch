'''Facial Expression Recognition using Professor's given data - Mominul'''

import matplotlib.pyplot as plt
import numpy as np
import torch
from torch import nn, optim
import torch.nn.functional as F
from torch.utils.data.sampler import SubsetRandomSampler
from torchvision import datasets, models, transforms
from tqdm.autonotebook import tqdm
import time
from CustomDataset import CustomImageDataset

# check if CUDA is available


device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
train_on_gpu = torch.cuda.is_available()
if not train_on_gpu:
    print('CUDA is not available.  Training on CPU ...')
else:
    print('CUDA is available!  Training on GPU ...')


# Create a transform pipeline (Compose)
transform = transforms.Compose([transforms.ToTensor(),
                              transforms.Normalize((0.5,), (0.5,)),
                              ])

# Loader parameters
batch_size = 9
num_workers = 0


# Get image dataset
train_data = CustomImageDataset(annotations_file='E:\Thesis\SampleDataset\ProfessorGivenData\labels.csv',
                                img_dir='E:\Thesis\SampleDataset\ProfessorGivenData\CK+_7_Contempt-20220601T100834Z-001\CK+_7_Contempt')

# Create Train, Validation and Test DataSet
slices = (int(0.6 * len(train_data)), int(0.2 * len(train_data)), int(0.2 * len(train_data)))

train_dataset, val_dataset, test_dataset = torch.utils.data.random_split(train_data, slices)

train_idx = list(range(len(train_dataset)))
val_idx = list(range(len(val_dataset)))
test_idx = list(range(len(test_dataset)))

# define samplers for obtaining training and validation batches
train_sampler = SubsetRandomSampler(train_idx)
valid_sampler = SubsetRandomSampler(val_idx)
test_sampler = SubsetRandomSampler(test_idx)

# Create Loaders for Train, Validation and Test Datasets
train_loader = torch.utils.data.DataLoader(train_data, batch_size=batch_size, sampler=train_sampler, num_workers=num_workers)
valid_loader = torch.utils.data.DataLoader(train_data, batch_size=batch_size, sampler=valid_sampler, num_workers=num_workers)
test_loader = torch.utils.data.DataLoader(train_data, batch_size=batch_size, sampler=test_sampler, num_workers=num_workers)

# Print Dataset Stats
print('# training images: ', len(train_sampler))
print('# validation images: ', len(valid_sampler))
print('# test images: ', len(test_sampler))
#print('Classes: ', train_data.classes)

# Visualize Some sample data

# Obtaning first batch of training images, through iterator of DataLoader
dataiter = iter(train_loader)
images, labels = dataiter.next()

labels_map = {0:'Neutral', 1:'Angry', 2:'Disgust', 3:'Contempt', 4:'Happy', 5:'Sad', 6:'Surprised'};

fig = plt.figure(figsize=(16,16));
columns = 3;
rows = 3;
for i in range(0, columns*rows):
    img_xy = i
    img = images[img_xy][0]
    fig.add_subplot(rows, columns, i+1)
    plt.title(str(labels_map[int(labels[img_xy])]))
    plt.axis('off')
    plt.imshow(img)
plt.show()


class CNN(nn.Module):
    def __init__(self):
        super(CNN, self).__init__()

        # layer #1
        self.layer1 = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=5, stride=1, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2))

        # convolutional layer #2
        self.layer2 = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=5, stride=1, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2))

        # convolutional layer #3
        self.layer3 = nn.Sequential(
            nn.Conv2d(128, 256, kernel_size=5, stride=1, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2))

        # convolutional layer #4
        self.layer4 = nn.Sequential(
            nn.Conv2d(256, 512, kernel_size=5, stride=1, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=2, stride=2))

        self.dropout = nn.Dropout(0.5)

        self.fc1 = nn.Linear(17920, 1024)
        self.fc2 = nn.Linear(1024, 10)

    def forward(self, x):
        # add sequence of convolutional and max pooling layers
        out = self.layer1(x)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = self.dropout(out)
        out = out.reshape(out.size(0), -1)
        out = self.fc1(out)
        out = self.fc2(out)
        return F.softmax(out, dim=1)


model = CNN()

# move tensors to GPU if CUDA is available
if train_on_gpu:
    model.cuda()

#print(model)

# Hyperparameters

# Loss = CrossEntropy
criterion = nn.CrossEntropyLoss()

# Optimize with SGD (Stochastic Gradient Descent)
optimizer = optim.SGD(model.parameters(), lr=0.001, momentum=0.9, weight_decay=0.0001)

# Epochs
num_epochs = 10


def train_model(model, trainloader, valloader, criterion, optimizer, num_epochs=10):
    start_ts = time.time()

    train_losses = []
    val_losses = []
    train_accuracy = []
    val_accuracy = []

    batches = len(trainloader)
    val_batches = len(valloader)

    valid_loss_min = np.Inf  # track change in validation loss

    # loop for every epoch (training + evaluation)
    for epoch in range(num_epochs):
        total_train_loss = 0

        # progress bar (works in Jupyter notebook too!)
        progress = tqdm(enumerate(trainloader), desc="Loss: ", total=batches)

        # ----------------- TRAINING  --------------------
        # set model to training
        model.train()

        train_running_corrects = 0
        val_running_corrects = 0

        for i, data in progress:
            X, y = data[0].to(device), data[1].to(device)

            # training step for single batch
            model.zero_grad()
            outputs = model(X)
            loss = criterion(outputs, y)
            loss.backward()
            optimizer.step()

            # getting training quality data
            current_train_loss = loss.item()
            total_train_loss += current_train_loss

            # convert output probabilities to predicted class
            _, preds_tensor = torch.max(outputs, 1)

            # calculate batch train accuracy
            current_train_accuracy = torch.sum(preds_tensor == y.data)
            train_running_corrects += current_train_accuracy

            # updating progress bar
            progress.set_description("Loss: {:.4f}".format(total_train_loss / (i + 1)))

        # releasing unnecessary memory in GPU
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        # ----------------- VALIDATION  -----------------
        # set model to evaluating (testing)

        total_val_loss = 0

        model.eval()
        with torch.no_grad():
            for i, data in enumerate(valloader):
                X, y = data[0].to(device), data[1].to(device)

                output = model(X)  # this get's the prediction from the network

                current_val_loss = criterion(output, y)
                total_val_loss += current_val_loss

                # convert output probabilities to predicted class
                _, preds_tensor = torch.max(output, 1)

                # calculate batch val accuracy
                current_val_accuracy = torch.sum(preds_tensor == y.data)
                val_running_corrects += current_val_accuracy

        epoch_train_acc = train_running_corrects.double() / len(train_sampler)
        train_accuracy.append(epoch_train_acc.numpy())

        epoch_val_acc = val_running_corrects.double() / len(valid_sampler)
        val_accuracy.append(epoch_val_acc.numpy())

        print(
            f"Epoch {epoch + 1}/{num_epochs}, training loss: {total_train_loss / batches},"
            f" validation loss: {total_val_loss / val_batches},"
            f" training acc: {epoch_train_acc * 100}, validation acc: {epoch_val_acc * 100}")

        train_losses.append(total_train_loss / batches)
        val_losses.append(total_val_loss / val_batches)

        # save model if validation loss has decreased
        if current_val_loss <= valid_loss_min:
            print('Validation loss decreased ({:.6f} --> {:.6f}).  Saving model ...'.format(
                valid_loss_min,
                current_val_loss))
            torch.save(model.state_dict(), 'faceCK+model.ckpt')
            valid_loss_min = current_val_loss

    print(f"Training time: {time.time() - start_ts}s")
    return np.squeeze(train_losses), np.squeeze(val_losses), np.squeeze(train_accuracy), np.squeeze(val_accuracy)


train_losses, val_losses, train_accuracy, val_accuracy = train_model(model,
                                                                     train_loader,valid_loader,
                                                                     criterion, optimizer, num_epochs)


def visualize_metrics(train_losses, val_losses, train_accuracy, val_accuracy):
    plt.figure(figsize=(16, 16));

    # Create Loss plot
    plt.title("Loss")
    plt.plot(range(num_epochs), train_losses)
    plt.plot(range(num_epochs), val_losses)
    plt.xlabel("Epochs")
    plt.ylabel("Loss")
    plt.tight_layout()
    plt.legend(['train', 'val'], loc="best")
    plt.show()

    plt.figure(figsize=(16, 16));

    # Create Accuracy plot
    plt.title("Accuracy Score")
    plt.plot(range(num_epochs), train_accuracy)
    plt.plot(range(num_epochs), val_accuracy)
    plt.xlabel("Epochs")
    plt.ylabel("Accuracy Score")
    plt.tight_layout()
    plt.ylim((0, 1.5))
    plt.legend(['train', 'val'], loc="best")
    plt.show()


visualize_metrics(train_losses, val_losses, train_accuracy, val_accuracy)


def visualize_test(model, testloader):
    # obtain one batch of test images
    dataiter = iter(testloader)
    images, labels = dataiter.next()

    labels_map = {0 :'Neutral', 1 :'Angry', 2 :'Disgust', 3:'Contempt', 4:'Happy', 5:'Sad', 6:'Surprised'};


    # move model inputs to cuda, if GPU available
    if train_on_gpu:
        images = images.cuda()

    # get sample outputs
    output = model(images)

    # convert output probabilities to predicted class
    _, preds_tensor = torch.max(output, 1)
    preds = np.squeeze(preds_tensor.numpy()) if not train_on_gpu else np.squeeze(preds_tensor.cpu().numpy())

    fig = plt.figure(figsize=(16, 16));
    columns = 3;
    rows = 3;
    for i in range(0, columns * rows):
        img_xy = i;
        img = images[img_xy][0]
        fig.add_subplot(rows, columns, i + 1)
        plt.title(str(labels_map[int(labels[img_xy])]) + " (" + labels_map[preds[i]] + ")")
        plt.axis('off')
        plt.imshow(img)
    plt.show()

visualize_test(model, test_loader)


''' reference  : https://github.com/fulviomascara/pytorch-cv/blob/master/notebook/.ipynb_checkpoints/pytorch-cbn-checkpoint.ipynb'''