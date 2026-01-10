# How does weighted KNN differ from standard KNN?

# Weighted KNN differ from standard KNN as  weighted KNN  focous more on the close values of k by  assigning higher weights based on distance.

#but in case of standard KNN all the values of k are equal i.e. there is no  such priority,all values of k are treated equally. 

#Thats make weighted more sensitive as compared to standard KNN.

# Also When data is even  standard KNN works good but in case of weighted KNN which works best when data is close to each other.




from sklearn.neighbors import KNeighborsClassifier


X = [[1], [2], [3], [10]]
y = [0, 0, 1, 1]


test_point = [[2.5]]


print( KNeighborsClassifier(n_neighbors=3, weights='uniform')
      .fit(X, y).predict(test_point))


print( KNeighborsClassifier(n_neighbors=3, weights='distance')
      .fit(X, y).predict(test_point))
