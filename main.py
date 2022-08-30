import torch_geometric.transforms as T
from prepareData import splitter, foldify, splitEdgesBasedOnFolds, extractId
import torch
import argparse
import torch_geometric
import numpy as np
from model import Model, test, train
from dataloader import dataloader

# Make everything reproducible
torch_geometric.seed_everything(3)
torch.manual_seed(0)
np.random.seed(0)
torch.use_deterministic_algorithms(True)

# Parsing CLI args.
parser = argparse.ArgumentParser(description='Options')
parser.add_argument('--dataset', help='dataset to use', type=str, default='LAGCN')
parser.add_argument('--epochs', help='number of epochs to train the model in',type=int, default=3000)
parser.add_argument('--thr-percent', help='the threshold percentage with respect to batch size',type=int, default=3)
parser.add_argument('--lr', help='learning rate for optimizer function',type=float, default=0.005)
parser.add_argument('--l', help='number of layers for graph convolutional encoder', type=int, default=2)
parser.add_argument('--n', help='number of neurons for each GCE layer', type=int, default=32)
parser.add_argument('--same', help='whether the same number of negatives should be selected as positives(interations)', type=lambda x: (str(x).lower() == 'true'), default=False)
parser.add_argument('--negative-split', help='how negatives should be involved in training and testing phase?', type=str, default='all')

args = parser.parse_args()
print(args)

# Setting the dynamic global variables
DATASET = args.dataset
EPOCHS = args.epochs
THRESHOLD_PERCENT = args.thr_percent
LEARNING_RATE= args.lr
LAYERS = args.l
NEURONS = args.n
SAME_NEGATIVE = args.same
NEGATIVE_SPLIT = args.negative_split
FOLDS = 5

def main():
    data, totalInteractions, totalNonInteractions, INTERACTIONS_NUMBER, NONINTERACTIONS_NUMBER = dataloader(DATASET)

    selectedInteractions, selectedNonInteractions = splitter(SAME_NEGATIVE, totalInteractions, totalNonInteractions, INTERACTIONS_NUMBER, NONINTERACTIONS_NUMBER)
    interactionsIndicesFolds, nonInteractionsIndicesFolds = foldify(selectedInteractions, selectedNonInteractions)

    metrics = np.zeros(7)

    for k in range(FOLDS):
        messageEdgesIndex, trainSuperVisionEdgesIndex, testSuperVisionEdgesIndex = splitEdgesBasedOnFolds(interactionsIndicesFolds, k)

        testNonEdgesIndex = nonInteractionsIndicesFolds[k]
        trainNonEdgesIndex = np.setdiff1d(nonInteractionsIndicesFolds.flatten(), testNonEdgesIndex, assume_unique=True)

        # edge_index does not need to be set in testing because otherwise causes data leak
        edge_index = [[], []]
        for drugIndex, diseaseIndex in selectedInteractions[messageEdgesIndex]:
            edge_index[0].append(drugIndex)
            edge_index[1].append(diseaseIndex)
        edge_index = torch.tensor(edge_index, dtype=torch.long)

        data['drug', 'treats', 'disease'].edge_index = edge_index

        #------------------Training------------------#
        edge_label_index = [[], []]
        neg_edge_label_index = [[], []]
        edge_label = []
        for drugIndex, diseaseIndex in selectedInteractions[trainSuperVisionEdgesIndex]:
            edge_label_index[0].append(drugIndex)
            edge_label_index[1].append(diseaseIndex)
            edge_label.append(1)
        if NEGATIVE_SPLIT == 'fold':
            for drugIndex, diseaseIndex in selectedNonInteractions[trainNonEdgesIndex]:
                neg_edge_label_index[0].append(drugIndex)
                neg_edge_label_index[1].append(diseaseIndex)
                edge_label.append(0)
        elif NEGATIVE_SPLIT == 'all':
            for drugIndex, diseaseIndex in selectedNonInteractions:
                neg_edge_label_index[0].append(drugIndex)
                neg_edge_label_index[1].append(diseaseIndex)
                edge_label.append(0)
        edge_label_index = torch.tensor(edge_label_index, dtype=torch.long)
        neg_edge_label_index = torch.tensor(neg_edge_label_index, dtype=torch.long)
        edge_label = torch.tensor(edge_label, dtype=torch.float)

        data['drug', 'treats', 'disease'].edge_label_index = torch.cat([edge_label_index, neg_edge_label_index],dim=-1)
        data['drug', 'treats', 'disease'].edge_label = edge_label

        data = T.ToUndirected()(data)
        data = T.AddSelfLoops()(data)
        data = T.NormalizeFeatures()(data)

        model = Model(data, neurons=NEURONS, layers=LAYERS)
        optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
        # for x, in model.parameters():
        #     print('x: ', x)

        # Due to lazy initialization, we need to run one model step so the number
        # of parameters can be inferred:
        with torch.no_grad():
            model.encoder(data.x_dict, data.edge_index_dict)

        criterion = torch.nn.BCEWithLogitsLoss()
        for epoch in range(1, EPOCHS):
            loss = train(data, model, optimizer, criterion)
            if epoch % 10 == 0:
                print('epoch: ', epoch, 'train loss: ', loss)
        
        #------------------Testing------------------#
        edge_label_index = [[], []]
        neg_edge_label_index = [[], []]
        edge_label = []
        for drugIndex, diseaseIndex in selectedInteractions[testSuperVisionEdgesIndex]:
            edge_label_index[0].append(drugIndex)
            edge_label_index[1].append(diseaseIndex)
            edge_label.append(1)
        if NEGATIVE_SPLIT == 'fold':
            for drugIndex, diseaseIndex in selectedNonInteractions[testNonEdgesIndex]:
                neg_edge_label_index[0].append(drugIndex)
                neg_edge_label_index[1].append(diseaseIndex)
                edge_label.append(0)
        elif NEGATIVE_SPLIT == 'all':
            for drugIndex, diseaseIndex in selectedNonInteractions:
                neg_edge_label_index[0].append(drugIndex)
                neg_edge_label_index[1].append(diseaseIndex)
                edge_label.append(0)
        edge_label_index = torch.tensor(edge_label_index, dtype=torch.long)
        neg_edge_label_index = torch.tensor(neg_edge_label_index, dtype=torch.long)
        edge_label = torch.tensor(edge_label, dtype=torch.float)
        
        data['drug', 'treats', 'disease'].edge_label_index = torch.cat([edge_label_index, neg_edge_label_index], dim=-1)
        data['drug', 'treats', 'disease'].edge_label = edge_label
        metric = test(data, model, THRESHOLD_PERCENT)
        metrics += metric

        print("calculated metrics in fold --> " + str(k + 1)+ ": ", metric)
    return metrics

metrics = main()
print("####### PARAMETERS #######", args)
print('####### FINAL RESULTS #######\n', metrics / FOLDS)

# extractId()