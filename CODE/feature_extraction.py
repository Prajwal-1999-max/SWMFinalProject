import pandas as pd
import numpy as np
import string
import re
import collections
from statistics import mean
from nltk.tokenize import sent_tokenize
from sklearn.metrics.pairwise import pairwise_distances
from scipy.stats import entropy
from imblearn.under_sampling import NearMiss
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, ConfusionMatrixDisplay
from sklearn.metrics import f1_score
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from tabulate import tabulate


def plotwordcloud(table):
    wc = WordCloud(background_color='white', min_font_size=10, width=500, height=500)
    reviews_wc = wc.generate(table[table['label'] == -1]['review'].str.cat(sep=" "))

    plt.figure(figsize=(8, 6))
    plt.imshow(reviews_wc)
    plt.title("Fake Reviews", fontsize=20)
    plt.show()
    reviews_wc = wc.generate(table[table['label'] == 1]['review'].str.cat(sep=" "))
    plt.figure(figsize=(8, 6))
    plt.imshow(reviews_wc)
    plt.title("Authentic Reviews", fontsize=20)
    plt.show()


def version2_undersample(input_table):
    target_labels = input_table["label"]
    excluded_columns = ['user_id', 'prod_id', 'label', 'date', 'review']
    feature_columns = [col for col in input_table.columns if col not in excluded_columns]
    processed_features = input_table[feature_columns]

    processed_features = processed_features.apply(lambda x: x / x.abs().max(), axis=0)

    feature_names = processed_features.columns.tolist()
    feature_matrix = processed_features.to_numpy()

    undersampler = NearMiss(version=3, n_neighbors_ver3=3)
    undersampled_features, undersampled_labels = undersampler.fit_resample(feature_matrix, target_labels)

    label_array = np.array([1 if label == -1 else 0 for label in undersampled_labels])

    return undersampled_features, label_array, feature_names


def undersample_data(input_table):
    random_state = 573
    class_sizes = input_table.groupby('label').size()
    min_class_size = class_sizes.min()

    undersampled_data = input_table.groupby('label').apply(
        lambda x: x.sample(n=min_class_size, random_state=random_state)).reset_index(drop=True)
    return undersampled_data


def pre_process(input_table):
    target_labels = input_table["label"]
    excluded_columns = ['user_id', 'prod_id', 'label', 'date', 'review']
    feature_columns = [col for col in input_table.columns if col not in excluded_columns]
    processed_features = input_table[feature_columns]

    processed_features = processed_features.apply(lambda x: x / x.abs().max(), axis=0)

    feature_names = processed_features.columns.tolist()
    feature_matrix = processed_features.to_numpy()
    label_array = np.array([1 if label == -1 else 0 for label in target_labels])

    return feature_matrix, label_array, feature_names


def preprocess_dataframe(input_table):
    excluded_columns = ['user_id', 'prod_id', 'label', 'date', 'review']
    feature_columns = [col for col in input_table.columns if col not in excluded_columns]
    processed_features = input_table[feature_columns]

    processed_features = processed_features.apply(lambda x: x / x.abs().max(), axis=0)

    return processed_features


def generate_metrics(true_labels, predicted_labels, evaluation_type):
    tn, fp, fn, tp = confusion_matrix(true_labels, predicted_labels).ravel()
    specificity = tn / (tn + fp)

    metric_names = ['Accuracy', 'Precision', 'Recall', 'Specificity', 'F1 Score']
    metric_values = [accuracy_score(true_labels, predicted_labels),
                     precision_score(true_labels, predicted_labels),
                     recall_score(true_labels, predicted_labels),
                     specificity,
                     f1_score(true_labels, predicted_labels)]

    metrics_df = pd.DataFrame(list(zip(metric_names, metric_values)), columns=["metric_type", "value"])
    metrics_df.to_csv(f"./EVALUATIONS/Metrics_{evaluation_type}.csv", header=False, index=False)

    confusion_matrix_data = {'Predicted Positive': [tp, fn],
                             'Predicted Negative': [fp, tn]}
    confusion_matrix_index = ['Actual Positive', 'Actual Negative']

    confusion_matrix_df = pd.DataFrame(confusion_matrix_data, index=confusion_matrix_index)

    print("\nConfusion Matrix:")
    print(tabulate(confusion_matrix_df, headers='keys', tablefmt='psql'))

    print("\nMetric Values:")
    print(tabulate(metrics_df, headers='keys', tablefmt='psql'))

def calculate_singleton(group):
    group_size = group.shape[0]
    return pd.Series([1 if group_size == 1 else 0] * group_size, index=group.index)


def metadata_view(input_table):
    input_table['singleton'] = input_table.groupby(['user_id', 'date']).apply(calculate_singleton).reset_index(
        drop=True)
    return input_table[['singleton']]

def textual_data_review(table):
    statistics_table = {"RationOfCapL": [], "RatioOfCapW": [
    ], "RatioOfFirstPerson": [], "RatioOfExclamation": []}
    first_person_pronouns = set(["i", "mine", "my", "me", "we", "our", "us", "ourselves", "ours"])

    for i, row in table.iterrows():
        sentences = sent_tokenize(row["review"])
        countExclamation = 0
        wordCountinAReview = 0
        countCapL = 0
        countCapW = 0
        countFirstP = 0
        for sentence in sentences:
            if sentence[-1] == "!":
                countExclamation += 1
            sentence = sentence.translate(
                str.maketrans('', '', string.punctuation))
            sentence = sentence.split(" ")

            wordCountinAReview += len(sentence)

            for word in sentence:
                if word.isupper():
                    countCapW += 1
                if word.lower() in first_person_pronouns:
                    countFirstP += 1
                for w in word:
                    if w.isupper():
                        countCapL += 1
                        break

        RatioOfExclamation = countExclamation / len(sentences)
        RationOfCapL = countCapL / wordCountinAReview
        RatioOfCapW = countCapW / wordCountinAReview
        RatioOfFirstPerson = countFirstP / wordCountinAReview
        statistics_table["RatioOfExclamation"].append(RatioOfExclamation)
        statistics_table["RationOfCapL"].append(RationOfCapL)
        statistics_table["RatioOfCapW"].append(RatioOfCapW)
        statistics_table["RatioOfFirstPerson"].append(RatioOfFirstPerson)

    text_statistics = pd.DataFrame.from_dict(statistics_table)
    return text_statistics

def table_burst_reviewer(table):
    
    grouped_data = table.groupby(['prod_id', 'date'])

    density = grouped_data.size().reset_index(name='density')
    table = table.merge(density, on=['prod_id', 'date'], validate='m:1')

    avg_date = grouped_data['rating'].mean().reset_index(name='avg_date')
    table = table.merge(avg_date, on=['prod_id', 'date'], validate='m:1')

    avg = table.groupby('prod_id')['rating'].mean().reset_index(name='avg')
    table = table.merge(avg, on='prod_id', validate='m:1')
    table['DFTLM'] = (table['rating'] - table['avg_date']).abs()
    table['MRD'] = (table['avg_date'] - table['avg']).abs()

    return table[['density', 'MRD', 'DFTLM']]



def extract_behavioral_features(table):
    review_count = table.groupby(['user_id', 'date']).size().reset_index(name='count')
    mnr = review_count.groupby('user_id')['count'].max().reset_index(name='MNR')
    table = table.merge(mnr, on='user_id', validate='m:1')

    total_reviews = table.groupby('user_id')['rating'].count().reset_index(name='total')
    positive_reviews = table[table['rating'] >= 4].groupby('user_id')['rating'].count().reset_index(name='pos')
    negative_reviews = table[table['rating'] <= 2].groupby('user_id')['rating'].count().reset_index(name='neg')
    merged_totals = total_reviews.merge(positive_reviews, on='user_id', how='left').fillna(0).merge(negative_reviews,
                                                                                                    on='user_id',
                                                                                                    how='left').fillna(
        0)
    merged_totals['PPR'] = merged_totals['pos'] / merged_totals['total']
    merged_totals['PNR'] = merged_totals['neg'] / merged_totals['total']
    table = table.merge(merged_totals[['user_id', 'PPR', 'PNR']], on='user_id', validate='m:1')

    table['review_length'] = table['review'].str.split().str.len()
    avg_review_length = table.groupby('user_id')['review_length'].mean().reset_index(name='RL')
    table = table.merge(avg_review_length, on='user_id', validate='m:1')

    avg_prod_rating = table.groupby('prod_id')['rating'].mean().reset_index(name='avg')
    table = table.merge(avg_prod_rating, on='prod_id', validate='m:1')
    table['rating_dev'] = (table['rating'] - table['avg']).abs()
    reviewer_dev = table.groupby('user_id')['rating_dev'].mean().reset_index(name='reviewer_dev')
    table = table.merge(reviewer_dev, on='user_id', validate='m:1')

    return table[['MNR', 'PPR', 'PNR', 'RL', 'rating_dev', 'reviewer_dev']]


def feature_extraction_rating(table):
    avg_prod_rating = table.groupby('prod_id')['rating'].mean().reset_index(name='prod_avg')
    table = table.merge(avg_prod_rating, on='prod_id', validate='m:1')
    table['avg_dev_from_entity_avg'] = (table['rating'] - table['prod_avg']).abs()

    user_rating_counts = table.groupby(['user_id', 'rating']).size().reset_index(name='count')
    user_total_counts = user_rating_counts.groupby('user_id')['count'].sum().reset_index(name='total_count')
    user_rating_counts = user_rating_counts.merge(user_total_counts, on='user_id', validate='m:1')
    user_rating_counts['prob'] = user_rating_counts['count'] / user_rating_counts['total_count']
    user_rating_entropy = user_rating_counts.groupby('user_id').apply(lambda x: entropy(x['prob'])).reset_index(
        name='rating_entropy')
    table = table.merge(user_rating_entropy, on='user_id', validate='m:1')

    avg_user_rating = table.groupby('user_id')['rating'].mean().reset_index(name='user_avg')
    table = table.merge(avg_user_rating, on='user_id', validate='m:1')
    table['rating_variance'] = (table['rating'] - table['user_avg']) ** 2

    return table[['avg_dev_from_entity_avg', 'rating_entropy', 'rating_variance']]


def extract_temporal_features(data):
    data['date'] = pd.to_datetime(data['date'])
    temp_data = data.loc[:, ['user_id', 'date', 'rating']]
    temp_data.sort_values(by=['date'], inplace=True)
    activity_time_table = temp_data[['user_id', 'date']].groupby(['user_id']).agg(
        first_date=pd.NamedAgg(column='date', aggfunc='min'),
        last_date=pd.NamedAgg(column='date', aggfunc='max')
    )
    activity_time_table['activity_time'] = (
            (activity_time_table['last_date'] - activity_time_table['first_date']) / np.timedelta64(1, 'D')).astype(int)

    temp_data2 = data
    temp_data2['date'] = pd.to_datetime(temp_data2['date'])
    temp_data2 = temp_data2[['user_id', 'date', 'rating']].groupby(['user_id', 'date']).agg(
        max_rating=pd.NamedAgg(column='rating', aggfunc='max')
    )

    temp_data['previous_date'] = temp_data.groupby('user_id')['date'].shift()
    temp_data['date_entropy'] = temp_data['date'] - temp_data['previous_date']
    temp_data.replace({pd.NaT: '0 day'}, inplace=True)
    temp_data['date_entropy'] = (temp_data['date_entropy'] / np.timedelta64(1, 'D')).astype(int)

    temp_data['original_index'] = temp_data.index
    temp_data3 = temp_data[['user_id', 'date']].groupby(['user_id']).agg(
        avg_date=pd.NamedAgg(column='date', aggfunc='mean')
    )
    temp_data = pd.merge(temp_data, temp_data3, on='user_id', how='left')
    temp_data['date_variance'] = abs(((temp_data['date'] - temp_data['avg_date']) / np.timedelta64(1, 'D'))) ** 2
    temp_data.set_index('original_index')

    data = data.loc[:, ['user_id', 'date']]
    data['date'] = pd.to_datetime(data['date'])
    data = pd.merge(data, activity_time_table, on='user_id', how='left')
    data = pd.merge(data, temp_data2, on=['user_id', 'date'], how='left')
    data = pd.merge(data, temp_data, left_on=data.index, right_on='original_index')

    return data[['activity_time', 'max_rating', 'date_entropy', 'date_variance']]
