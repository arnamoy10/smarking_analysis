from sklearn import svm
from sklearn.covariance import EllipticEnvelope
from sklearn.ensemble import IsolationForest
import numpy as np

data = np.array([[1,1],[1,1],[1,2],[2,3],[1.2,1.5],[1.2,1.75],[1,2.1]])

clf = svm.OneClassSVM(nu=0.95 * 0.25 + 0.05, kernel="rbf", gamma=0.1)
clf.fit(data)
y_pred = clf.predict(data)

print y_pred


data = np.array([[1,1],[1,1],[1,2],[2,3],[1.2,1.5],[1.2,1.75],[1,2.1]])
clf = EllipticEnvelope(contamination=0.25)
clf.fit(data)
y_pred = clf.predict(data)

print y_pred

data = [[1,1],[1,1],[1,2],[2,3],[1.2,1.5],[1.2,1.75],[1,2.1]]

rng = np.random.RandomState(42)

clf = IsolationForest( contamination=0.25, random_state=rng)
clf.fit(data)
y_pred = clf.predict(data)

print y_pred
