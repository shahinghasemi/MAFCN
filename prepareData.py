import matplotlib
import numpy as np
import scipy.io as sio
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

# def Cosine(matrix)
def Jaccard(matrix):
    matrix = np.mat(matrix)
    numerator = matrix * matrix.T
    denominator = np.ones(np.shape(matrix)) * matrix.T + matrix * np.ones(np.shape(matrix.T)) - matrix * matrix.T
    return np.array(numerator / denominator)

def readFromMat():
    data = sio.loadmat('./data/SCMFDD_Dataset.mat')
    print(data.keys())
    np.savetxt('./structure_feature_matrix.txt', np.array(data['structure_feature_matrix']))
    np.savetxt('./target_feature_matrix.txt', np.array(data['target_feature_matrix']))
    np.savetxt('./enzyme_feature_matrix.txt', np.array(data['enzyme_feature_matrix']))
    np.savetxt('./pathway_feature_matrix.txt', np.array(data['pathway_feature_matrix']))

def plot(X, Y, label):
    print('about to draw: X.shape: ', X.shape, 'Y.shape: ', Y.shape)
    plt.scatter(X, Y, c='b', marker='o', linewidth=0, s=15, alpha=0.8, label=label)

def prepareDrugData(featureList, embeddingMethod):
    featureMatrixDic = {}
    finalDic = {}

    for feature in featureList:
        matrix = np.loadtxt('./data/'+ feature+ '_feature_matrix.txt')
        featureMatrixDic[feature] = matrix
    
    if embeddingMethod == 'AE' or embeddingMethod == 'matrix':
        finalDic = featureMatrixDic;

    elif embeddingMethod == 'jaccard':
        for feature, matrix in featureMatrixDic.items():
            finalDic[feature] = Jaccard(matrix)
            
    elif embeddingMethod == 'PCA':
        for feature, matrix in featureMatrixDic.items():
            pca = PCA(n_components=2)
            transformed = pca.fit_transform(matrix)
            finalDic[feature] = transformed
    else:
        exit('please provide a known embedding method')
    # elif similarity == 'cosine':
    
    return finalDic


