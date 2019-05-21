import pandas as pd
from shapely import wkt
import sys

def parseArgs():
	"""Parse the system arguments into a list.
	Finds all the arguments in the form key=value and assign them to a list.

	returns list
	"""
	args = sys.argv
	arguments = {}
	for arg in args:
		if arg.find('=') != -1:
			elem = arg.split('=')
			arguments[elem[0]] = elem[1]

	return arguments

def isNaN(value):
	"""Checks if value is NaN.

	returns boolean
	"""
	return value != value

def SameWKT(arg_by_ref):
	"""Finds POIs with the same geometry.
	It removes from dataset all POIs with the same geometry and places them in a new dataset.

	arg_by_ref -- The array containing as first item the initial dataset

	returns dataset -- The dataset containing POIs with the same geometry
	"""
	data = arg_by_ref[0]
	unique = data.WKT.unique()
	definition = list(data.columns.values)
	P = pd.DataFrame(columns=definition)
	D = pd.DataFrame(columns=definition)
	for wkt in unique:
		row = data.loc[data.WKT == wkt]
		length = row.WKT.count()
		if length == 1:
			P = P.append(row)
		else:
			D = D.append(row)

	arg_by_ref[0] = P
	return D

def findMatches(arg_by_ref, checkForName=False):
	"""Finds POIs with the same geometry in 2 datasets.
	For each POI in the first dataset, check whether there is a corresponding POI in the 2nd one.
	If it exists, move the POI from the second dataset to a resulting dataset B. In any case, the
	POIs from the first dataset are going to be moved in the resulting dataset A.

	arg_by_ref array -- The array containing the 2 datasets
	checkForName boolean -- Whether to also check for same name

	returns tuple -- The two resulting datasets
	"""
	dataA = arg_by_ref[0]
	dataB = arg_by_ref[1]

	definition = list(dataA.columns.values)
	res_A = pd.DataFrame(columns=definition)
	res_B = pd.DataFrame(columns=definition)

	for index, poiA in dataA.iterrows():
		wkt = poiA.WKT
		if checkForName:
			poiB = dataB.loc[(dataB.WKT == wkt) & (dataB[NAME] == poiA[NAME])]
		else:
			poiB = dataB.loc[dataB.WKT == wkt]
		exists = (poiB.WKT.count() > 0)

		if exists:
			res_B = res_B.append(poiB)
			dataB = dataB.drop(poiB.index)

		res_A = res_A.append(poiA)
		dataA = dataA.drop(index)

	arg_by_ref[0] = dataA
	arg_by_ref[1] = dataB

	return (res_A, res_B)

def calculateScore(score, dataA, dataB, checkForName=False):
	"""Calculates the score comparing the corresponding fields of 2 datasets.

	score double -- The initial score
	dataA dataframe -- The first dataset
	dataB dataframe -- The second dataset

	returns double -- The calculated score
	"""
	penalties = {
		'WKT': 1.0,
		NAME: 0.5,
		ADDRESS: 0.3,
		PHONE: 0.1
	}
	columns = list(dataA.columns.values)
	for indexA, poiA in dataA.iterrows():
		if (checkForName):
			candIDates = dataB.loc[(dataB.WKT == poiA.WKT) & (dataB[NAME] == poiA[NAME])]
		else:
			candIDates = dataB.loc[dataB.WKT == poiA.WKT]
		if candIDates.index.size == 0:
			continue
		poiB = candIDates.loc[candIDates.index[0]]
		score += 1
		for field in columns:
			if (isNaN(poiA[field]) and isNaN(poiB[field])) or str(poiA[field]).lower() == str(poiB[field]).lower() or poiB[field] == '' or isNaN(poiB[field]):
				continue
			if field in penalties:
				penalty = penalties[field]
			else:
				penalty = 0.1
			# print('Penalty for', field, ':', penalty)
			# print(poiA[field], poiB[field])
			# print()
			score -= penalty

	return score


"""Main procedure
Arguments:
	ID -- The name of the unique key of the datasets
	fileA -- The full path of the first dataset
	fileB -- The full path of the second dataset
	name -- The 'name' field of the datasets
	address -- The 'address' field of the datasets
	phone -- The 'phone' field of the datasets
"""

args = parseArgs()
ID = args['id']
NAME = args['name']
ADDRESS = args['address']
PHONE = args['phone']

print(args['fileA'], '-', args['fileB'])
# exit()

MP = pd.read_csv(args['fileA'], index_col=ID)
SP = pd.read_csv(args['fileB'], index_col=ID)

geometry = MP.WKT.apply(wkt.loads)
geometry = geometry.apply(wkt.dumps, rounding_precision=5)
MP.WKT = geometry

geometry = SP.WKT.apply(wkt.loads)
geometry = geometry.apply(wkt.dumps, rounding_precision=5)
SP.WKT = geometry

numberOfPOIs = MP.index.size

wrapper = [MP]
MD = SameWKT(wrapper)
MP = wrapper[0]

wrapper = [SP]
SD = SameWKT(wrapper)
SP = wrapper[0]

# Initialize the score
score = 0.0

# Find matching geometries for the 2 datasets (single geometry)
wrapper = [MP, SP]
(MM, SM) = findMatches(wrapper)
# print(MM, SM)
MP = wrapper[0]
SP = wrapper[1]

# Add 1 point for each match
score += 1.0*SM.index.size
# Remove 0.5 point for each remaining unmatched POI
# print('Remove', 0.5*SP.index.size, 'points')
score -= 0.5*SP.index.size

# Examine the remaining features of the matched POIs
score = calculateScore(score, MM, SM)

# Same procedure for double geometries
wrapper = [MD, SD]
(MDM, SDM) = findMatches(wrapper, checkForName=True)
MD = wrapper[0]
SD = wrapper[1]

score += 1.0*SDM.index.size
score = calculateScore(score, MDM, SDM, checkForName=True)
# print('Remove', 0.5*SD.index.size, 'points')
score -= 0.5*SD.index.size

# Normalize the score
score = score/(2*numberOfPOIs)


print('Score:', round(score*100, 1))
