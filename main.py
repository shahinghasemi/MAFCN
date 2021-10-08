import torch
from autoencoder import trainAutoEncoders
from prepareData import prepareData
import numpy as np
from FNN import trainFNN
from metrics import calculateMetric
import argparse

parser = argparse.ArgumentParser(description='Options')
parser.add_argument('--emb', help='auto-encoder embedding size',type=int, default=32)
parser.add_argument('--emb-method', help='embedding method for drug features', type=str, default='AE')
parser.add_argument('--feature-list', help='the feature list to include', type=str, nargs="+")
parser.add_argument('--folds', help='number of folds for cross-validation',type=int,  default=5)
parser.add_argument('--batch-auto', help='batch-size for auto-encoder',type=int, default=1000)
parser.add_argument('--batch-model', help='batch-size for DNN',type=int, default=1000)
parser.add_argument('--epoch-auto', help='number of epochs to train in auto-encoder',type=int, default=20)
parser.add_argument('--epoch-model', help='number of epochs to train in model',type=int, default=20)
parser.add_argument('--dropout', help='dropout probability for DNN',type=float, default=0.3)
parser.add_argument('--lr-model', help='learning rate for DNN',type=float, default=0.001)
args = parser.parse_args()
print(args)
EMBEDDING_DEM = args.emb
FEATURE_LIST = args.feature_list
N_INTERACTIONS = 18416
N_NON_INTERACTIONS = 142446
N_EPOCHS_AUTO = args.epoch_auto
N_EPOCHS_MODEL = args.epoch_model
N_BATCHSIZE_MODEL = args.batch_model
N_BATCHSIZE_AUTO = args.batch_auto
EMBEDDING_METHOD = args.emb_method
FOLDS = args.folds
DROPOUT = args.dropout
LEARNING_RATE_MODEL = args.lr_model
DRUG_NUMBER = 269
DISEASE_NUMBER = 598

def crossValidation(drugDic, diseaseSim, drugDisease, interactionIndices, nonInteractionIndices):
    metrics = np.zeros(7)
    # To be dividable by 5
    totalInteractionIndex = np.arange(N_INTERACTIONS - 1)
    totalNonInteractionIndex = np.arange(N_NON_INTERACTIONS - 1)

    np.random.shuffle(totalInteractionIndex)
    np.random.shuffle(totalNonInteractionIndex)

    totalInteractionIndex = totalInteractionIndex.reshape(FOLDS, N_INTERACTIONS // FOLDS)
    totalNonInteractionIndex = totalNonInteractionIndex.reshape(FOLDS, N_NON_INTERACTIONS // FOLDS)

    for k in range(FOLDS):
        testInteractionsIndex = totalInteractionIndex[k]
        trainInteractionsIndex = np.setdiff1d(totalInteractionIndex.flatten(), testInteractionsIndex, assume_unique=True)

        testNonInteractionsIndex = totalNonInteractionIndex[k]
        trainNonInteractionsIndex = np.setdiff1d(totalNonInteractionIndex.flatten(), testNonInteractionsIndex, assume_unique=True)

        autoEncoders = []
        allFeatureEmbeddings = []
        for featureIndex in range(len(FEATURE_LIST)):
            involvedDiseases = []
            XTrain = []
            YTrain = []
            for drugIndex, diseaseIndex in interactionIndices[trainInteractionsIndex]:
                drug = drugDic[FEATURE_LIST[featureIndex]][drugIndex]
                XTrain.append(drug)
                involvedDiseases.append(diseaseSim[diseaseIndex])
                YTrain.append([1])
            
            interactions = len(YTrain)

            for drugIndex, diseaseIndex in nonInteractionIndices[trainNonInteractionsIndex]:
                drug = drugDic[FEATURE_LIST[featureIndex]][drugIndex]
                XTrain.append(drug)
                involvedDiseases.append(diseaseSim[diseaseIndex])
                YTrain.append([0])

            nonInteractions = len(YTrain) - interactions
            print('train: interactions: ', interactions, 'non-interactions: ', nonInteractions)

            XTrain = np.array(XTrain)
            featureEmbeddings = []
            if EMBEDDING_METHOD == 'AE':
                autoEncoders.append(trainAutoEncoders(XTrain, N_EPOCHS_AUTO, N_BATCHSIZE_AUTO))
                for i in range(len(XTrain)):
                    embedding = autoEncoders[featureIndex].encode(torch.tensor(XTrain[i]).float(), True)
                    featureEmbeddings.append(embedding)
            else:
                for i in range(len(XTrain)):
                    embedding = XTrain[i]
                    featureEmbeddings.append(embedding)

            allFeatureEmbeddings.append(featureEmbeddings)
        
        for i in range(len(FEATURE_LIST)):
            if i == 0:
                XTrain = allFeatureEmbeddings[i]
            else:
                # concatenating all drug's feature
                XTrain = np.hstack((XTrain, allFeatureEmbeddings[i]))
    
        # concatenating concatenated drugs with diseases
        XTrain = np.hstack((XTrain, involvedDiseases))
        YTrain = np.array(YTrain)
        dataTrain = np.hstack((XTrain, YTrain))
        trainedModel = trainFNN(dataTrain, N_EPOCHS_MODEL, N_BATCHSIZE_MODEL, DROPOUT, LEARNING_RATE_MODEL)

        # TESTING
        allFeatureEmbeddings = []
        for featureIndex in range(len(FEATURE_LIST)):
            XTest = []
            YTest = []
            involvedDiseases = []
            for drugIndex, diseaseIndex in interactionIndices[testInteractionsIndex]:
                drug = drugDic[FEATURE_LIST[featureIndex]][drugIndex]
                XTest.append(drug)
                involvedDiseases.append(diseaseSim[diseaseIndex])
                YTest.append([1])

            interactions = len(YTest)

            for drugIndex, diseaseIndex in nonInteractionIndices[testNonInteractionsIndex]:
                drug = drugDic[FEATURE_LIST[featureIndex]][drugIndex]
                XTest.append(drug)
                involvedDiseases.append(diseaseSim[diseaseIndex])
                YTest.append([0])

            nonInteractions = len(YTest) - interactions
            print('test: interactions: ', interactions, 'non-interactions: ', nonInteractions)

            featureEmbeddings = []
            if EMBEDDING_METHOD == 'AE':
                autoEncoders.append(trainAutoEncoders(XTest, N_EPOCHS_AUTO, N_BATCHSIZE_AUTO))
                for i in range(len(XTest)):
                    embedding = autoEncoders[featureIndex].encode(torch.tensor(XTest[i]).float(), True)
                    featureEmbeddings.append(embedding)
            else:
                for i in range(len(XTest)):
                    embedding = XTest[i]
                    featureEmbeddings.append(embedding)

            allFeatureEmbeddings.append(featureEmbeddings)
        
        for i in range(len(FEATURE_LIST)):
            if i == 0:
                XTest = allFeatureEmbeddings[i]
            else:
                # concatenating all drug's feature
                XTest = np.hstack((XTest, allFeatureEmbeddings[i]))

        XTest = np.hstack((XTest, involvedDiseases))
        YTest = np.array(YTest)
        y_pred_prob = trainedModel(torch.tensor(XTest).float()).detach().numpy()

        metric = np.array(calculateMetric(YTest, y_pred_prob))
        metrics += metric
        print('metric: ', metric)

    return metrics

def main():
    print('nDrugs: ', DRUG_NUMBER)
    print('nDisease: ', DISEASE_NUMBER)
    
    drugDic = prepareData(FEATURE_LIST, EMBEDDING_METHOD)

    # read the interactions matrix
    drugDisease = np.loadtxt('./data/drug_dis.csv', delimiter=',')
    diseaseSim = np.loadtxt('./data/dis_sim.csv', delimiter=',')
    interactionIndices = np.array(np.mat(np.where(drugDisease == 1)).T) #(18416, 2)
    nonInteractionIndices = np.array(np.mat(np.where(drugDisease == 0)).T) #(142446, 2)
    results = crossValidation(drugDic, diseaseSim, drugDisease, interactionIndices, nonInteractionIndices)
    print('results: ', results / FOLDS)

main()
