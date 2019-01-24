'''
Created on 12 Jan 2015
 
 Constructs an entity grid from a given file containing ptb trees. The file may be English, French or German.
 The entity grid uses the Stanford Parser to identify all nouns in the input text.
 For the English version it additionally determines the grammatical role played by that entity in each particular occurance. 
 The various options are set on the commandline, to ensure correct parser is set.
 
 @author Karin Sim

'''
import argparse
import sys
import traceback
import logging
import gzip
from grid import r2i, i2r
import StanfordDependencies
import numpy as np
from discourse.doctext import iterdoctext, writedoctext
from discourse.util import smart_open, read_documents
from collections import defaultdict

from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet as wn

wnl = WordNetLemmatizer()

def get_POS(pos_tb):
    first_lower = pos_tb[0].lower()
    if first_lower not in ['v', 'n', 'a', 'r']:
        return 'n'
    return first_lower

# nouns = ['NNP', 'NP','NNS','NN','N','NE']
# a hack to include pronouns
nouns = ['NNP', 'NP','NNS','NN','N','NE', 'PRP', 'FW']

''' csubj,  
    csubjpass, {xsubj}: controlling subject}, 
    subj,  
    nsubj (nominal subject), 
    nsubjpass
    '''
subject =[ 'csubj', 'csubjpass','subj','nsubj','nsubjpass']

''' pobj (object of a preposition) 
    also dobj ( direct object) 
    and iobj ( indirect object )'''
object= ["pobj","dobj","iobj"] 



def open_file(path):
    if path.endswith('.gz'):
        return gzip.open(path)
    else:
        return open(path)
        
# input is in form of ptb trees. 
def main(args):
    """ Extract entities and construct grid """
    try:
        #for ipath in enumerate(ipaths): 
        #with gzip.open(input_path, 'rb') as fi:

        #with gzip.open(input_path+'_grid' + '.gz', 'wb') as fo:

        with open(args.directory, 'rb' ) as fi, \
         open(args.directory+'_grid', 'w') as fo:
            text_idx = 0
            grids = []
            for lines, attrs in iterdoctext(fi):
                logging.debug('document %s', attrs['id'])
                print ' extract '+str(len(lines))+' lines'

                print >> fo, "# docid=" + attrs['id']
                print >> fo, "# id=" + text_idx

                entities, sent_num = extract_grids(lines)
                print entities
                
                grid = construct_grid(entities, sent_num)
                grids.append(grid)
                print grid

                output_grid(grid, fo)
                #writedoctext(fo, grid , id=attrs['id'])
                text_idx+=1
            logging.info('done: %s', args.directory)
    except:
        raise Exception(''.join(traceback.format_exception(*sys.exc_info())))       
            
def extract_grids(lines):
    """ Identify entities from ptb trees for document. store in dictionary for grid construction. """

    entities = defaultdict(lambda : defaultdict(dict))
    #print 'fi='+fi

    sent_idx = 0
    for line in lines:
        entities, tokens = convert_tree(line, entities, sent_idx)
        sent_idx+=1
        
    return entities, sent_idx
                
            
        
#from dependencies extract nouns with their grammatical dependencies in given sentence
def convert_tree(line, entities, sent_id):
    print ' convert_tree with '+line
    sd = StanfordDependencies.get_instance(
            jar_filename='/root/xhong/stanford/stanford-corenlp-full-2018-10-05/stanford-corenlp-3.9.2.jar',
            backend='subprocess')
    
    #ex='(ROOT(S(NP (PRP$ My) (NN dog))(ADVP (RB also))(VP (VBZ likes)(S(VP (VBG eating)(NP (NN sausage)))))(. .)))'
    #dependencies = sd.convert_tree(ex, debug=True)
    
    idx = 0
    #returns a list of sentences (list of list of Token objects) 
    dependencies = sd.convert_tree(line, debug=True)

    for token in dependencies:
        print token
        if token.pos in nouns :
            print ' .. is a noun-'+token.pos
            grammatical_role = '-'
            if token.deprel in subject: 
                grammatical_role = 'S'
            elif token.deprel in object:
                grammatical_role = 'O'
            else:
                grammatical_role = 'X'
            
            # print token.form
            token_lemma = wnl.lemmatize(token.form, get_POS(token.pos))
            print token.form, token_lemma
            ''' if this entity has already occurred in the sentence, store the reference with highest grammatical role , 
            judged here  as S > O > X '''
            if token_lemma in entities and entities[token_lemma][sent_id] :
                print str(entities[token_lemma][sent_id]) + ' comparing to '+str(r2i[grammatical_role])
                if (entities[token_lemma][sent_id]) < r2i[grammatical_role]:
                    entities[token_lemma][sent_id] = r2i[grammatical_role]
            else:
                entities[token_lemma][sent_id] = r2i[grammatical_role]
            ''' entity->list of : sentence_number->grammatical_role'''
        idx +=1

    # print entities
    return entities, idx
    
def construct_grid(entities, sentences):
    """ #construct grid from dictionary, rows are sentences, cols are entities """
    print 'size='+str(len(entities))
    y = len(entities)
    print (sentences, y)

    grid = np.zeros((sentences, y))
    entity_idx = 0
    for entity in entities.keys():
        occurances = entities[entity]
        for sentence in occurances :
            grid[sentence][entity_idx] = occurances[sentence] 
        entity_idx+=1
    
    # print grid
    return grid

def output_grid(grid, ostream):
    """ output grid  """
    output = ''

    #print >> ostream, '# %s' % attr_str
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]): #each char representing entity
            if grid[i][j] == 0:
                output += '-'
            else:
                output += i2r[grid[i][j]]
        output += '\n'
    output += '\n'
    print >> ostream, output
            
def parse_args():
    """parse command line arguments"""
    
    parser = argparse.ArgumentParser(description='implementation of Entity grid using ptb trees as input',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    #parser.description = 'implementation of Entity grid'
    #parser.formatter_class = argparse.ArgumentDefaultsHelpFormatter
    
    parser.add_argument('directory', 
            type=str,
            #argparse.FileType('rb'),
            help="path for input file")
    
    #parser.add_argument('language', 
    #        type=argparse.FileType('r'),
    #        help="language of input file: one of English, French or German")
    parser.add_argument('--verbose', '-v',
            action='store_true',
            help='increase the verbosity level')
    
    args = parser.parse_args()
    
    logging.basicConfig(
            level=(logging.DEBUG if args.verbose else logging.INFO), 
            format='%(levelname)s %(message)s')
    return args

if __name__ == '__main__':
     main(parse_args())