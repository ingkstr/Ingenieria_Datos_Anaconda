import argparse
import hashlib
import logging
logging.basicConfig(level=logging.INFO)
from urllib.parse import urlparse
import pandas as pd
import nltk
from nltk.corpus import stopwords

logger = logging.getLogger(__name__)
stop_words = set(stopwords.words('spanish'))

def main(filename):
    """Función principal de lectura y manipulación de datos"""
    logger.info('Starting cleaning process')
    df = _read_data(filename)
    newspaper_uid = _extract_newspaper_uid(filename)

    df = _add_newspaper_uid_column(df, newspaper_uid)
    df = _extract_host(df)
    df = _fill_missing_titles(df)
    df = _generate_uids_for_rows(df)
    df = _remove_new_lines_from_body(df)
    df['n_tokens_title'] = _tokenize_columns(df,'title')
    df['n_tokens_body'] = _tokenize_columns(df,'body')
    df = _remove_duplicates_entries(df,'title')
    df = _drop_rows_with_missing_values(df)
    _save_data(df, filename)
    return df

def _read_data(filename):
    """Lectura de archivo a domar"""
    logger.info('Reading file {}'.format(filename))
    return pd.read_csv(filename)

def _extract_newspaper_uid(filename):
    """Extracción de nombre de página web basado en el título del archivo"""
    logger.info('Extracting newspaper uid')
    newspaper_uid = filename.split('/')[-1].split('_')[0]
    logger.info('Newspaper uid detected: {}'.format(newspaper_uid))
    return newspaper_uid

def _add_newspaper_uid_column(df, newspaper_uid):
    """Inserción de columna de uid al DataFrame"""
    logger.info('Filling newspaper uid column with {}'.format(newspaper_uid))
    df['newspaper_uid'] = newspaper_uid
    return df

def _extract_host(df):
    """Extracción de host de las urls"""
    logger.info('Extracting host from urls')
    df['host'] = df['url'].apply(lambda url: urlparse(url).netloc)
    return df

def _fill_missing_titles(df):
    """Llenado de títulos faltantes"""
    logger.info('Filling missing titles')
    missing_titles_mask = df['title'].isna()
    missing_titles = (df[missing_titles_mask]['url']
                  .str.extract(r'(?P<missing_titles>[^/]+)$')
                  .applymap(lambda title: title.split('-'))
                  .applymap(lambda title_word_list: ' '.join(title_word_list)))
    df.loc[missing_titles_mask, 'title'] =  missing_titles.loc[:,'missing_titles']
    return df

def _generate_uids_for_rows(df):
    """Generador de ID's"""
    logger.info('Generate uids for every rows')
    uids = (df
        .apply(lambda row: hashlib.md5(bytes(row['url'].encode())), axis=1)
        .apply(lambda hash_object: hash_object.hexdigest())
        )
    df['uid'] = uids
    return df.set_index('uid')


def _remove_new_lines_from_body(df):
    """Retira saltos de líneas"""
    logger.info('Remove new lines from body')
    stripped_body = (df
                 .apply(lambda row: row['body'], axis=1)
                 .apply(lambda body: list(body))
                 .apply(lambda letters: list(map(lambda letter: letter.replace('\n',''), letters)))
                 .apply(lambda letters: ''.join(letters))
                )
    df['body'] = stripped_body
    return df

def _tokenize_columns(df, column_name):
    """Tokeniza la columna deseada en el dataframe"""
    logger.info('Tokenizing {} column in df dataframe'.format(column_name))
    return (df
           .dropna()
           .apply(lambda row: nltk.word_tokenize(row[column_name]), axis=1)
           .apply(lambda tokens: list(filter(lambda token: token.isalpha(),tokens)))
           .apply(lambda tokens: list(map(lambda token: token.lower(),tokens)))
           .apply(lambda word_list: list(filter(lambda word: word not in stop_words, word_list)))
           .apply(lambda valid_word_list: len(valid_word_list))
           )

def _remove_duplicates_entries(df,column_name):
    """Función para remover elementos con duplicados en la columna deseada"""
    logger.info('Removing duplicate entries')
    df.drop_duplicates(subset=[column_name],keep='first', inplace=True)
    return df

def _drop_rows_with_missing_values(df):
    """Función para quitar información sin valores"""
    logger.info('Dropping rows with missing values')
    return df.dropna()

def _save_data(df, filename):
    """Guardado de archivo"""
    clean_filename = filename.replace(".csv", "_cleaned.csv").split("/")[-1]

    logger.info('Saving data at location: {}'.format(clean_filename))
    df.to_csv(clean_filename)

if __name__ == '__main__':
    """Función de arranque de script Python"""
    parser = argparse.ArgumentParser()
    parser.add_argument('filename',
                        help='Path of dirty data',
                        type=str)
    arg = parser.parse_args()
    df = main(arg.filename)
    print(df)
