#!/usr/bin/python

import numpy as np
import struct
import sys
import os
import os.path

from SGFParser import *
from Board import *

def make_stone_plane(array, board, stone):
    #for x in xrange(board.N):
    #    for y in xrange(board.N):
    #        if board[x,y] == stone: array[x,y] = 1
    np.copyto(array, np.equal(board.vertices, stone))

def make_ones_plane(array, board):
    np.copyto(array, np.ones((board.N, board.N)))

def make_history_planes(array, board, max_lookback):
    assert array.shape[2] == max_lookback
    for lookback in xrange(max_lookback):
        if lookback < len(board.move_history):
            x,y = board.move_history[lookback]
            array[x,y,lookback] = 1

def find_group(board, start_x, start_y):
    group_xys = [(start_x, start_y)]
    visited = np.zeros((board.N, board.N), dtype=np.bool_) 
    visited[start_x, start_y] = True
    group_color = board[start_x, start_y]
    i = 0
    while i < len(group_xys):
        x,y = group_xys[i]
        i += 1
        for dx,dy in dxdys:
            adj_x, adj_y = x+dx, y+dy
            if board.is_on_board(adj_x, adj_y):
                adj_stone = board[adj_x, adj_y]
                if adj_stone == group_color and not visited[adj_x, adj_y]:
                    group_xys.append((adj_x, adj_y))
                    visited[adj_x, adj_y] = True
    return group_xys

def count_group_liberties(board, start_x, start_y):
    group_xys = [(start_x, start_y)]
    visited = np.zeros((board.N, board.N), dtype=np.bool_) 
    visited[start_x, start_y] = True
    group_color = board[start_x, start_y]
    liberties = set()
    i = 0
    while i < len(group_xys):
        x,y = group_xys[i]
        i += 1
        for dx,dy in dxdys:
            adj_x, adj_y = x+dx, y+dy
            if board.is_on_board(adj_x, adj_y):
                adj_stone = board[adj_x, adj_y]
                if adj_stone == Stone.Empty:
                    liberties.add((adj_x, adj_y))
                elif adj_stone == group_color and not visited[adj_x, adj_y]:
                    group_xys.append((adj_x, adj_y))
                    visited[adj_x, adj_y] = True
    return len(liberties)

def make_liberty_count_planes(array, board, Nplanes):
    assert array.shape[2] == Nplanes
    for x in xrange(board.N):
        for y in xrange(board.N):
            if board[x,y] != Stone.Empty:
                num_liberties = board.count_group_liberties(x, y)
                if num_liberties > Nplanes: num_liberties = Nplanes
                array[x,y,num_libiertes-1] = 1

def make_liberty_count_after_move_planes(array, board, Nplanes, stone):
    assert array.shape[2] == Nplanes
    for x in xrange(board.N):
        for y in xrange(board.N):
            if board[x,y] != Stone.Empty:
                board.save()
                if board.play_stone(x, y, stone):
                    num_liberties = board.count_group_liberties(x, y)
                    if num_liberties > Nplanes: num_liberties = Nplanes
                    array[x,y,num_libiertes-1] = 1
                board.restore()

def make_self_atari_size_planes(array, board, Nplanes, stone):
    assert array.shape[2] == Nplanes
    for x in xrange(board.N):
        for y in xrange(board.N):
            if board[x,y] != Stone.Empty:
                board.save()
                if board.play_stone(x, y, stone):
                    num_liberties = board.count_group_liberties(x, y)
                    if num_liberties == 1:
                        group_size = len(find_group(board, x, y))
                        if group_size > Nplanes: group_size = Nplanes
                        array[x,y,group_size-1] = 1
                board.restore()

def count_stones(board, color):
    return np.count_nonzero(np.equal(board.vertices, color))

def count_captured_stones(board, x, y, stone):
    opponent_color = flipped_stone(stone)
    num_opponent_stones = count_stones(board, opponent_color)
    num_captured = 0
    if board[x, y] == Stone.Empty:
        board.save()
        if board.play_stone(x, y, stone, just_testing=True):
            num_captured = num_opponent_stones - count_stones(board, opponent_color)
        board.restore()
    return num_captured

def make_capture_count_planes(array, board, max_capture_count, play_color):
    assert array.shape[2] == max_capture_count
    for x in xrange(board.N):
        for y in xrange(board.N):
            if board[x,y] == Stone.empty:
                num_captured = count_captured_stones(board, x, y, play_color)
                if num_captured >= max_capture_count: num_captured = max_capture_count-1
                array[x,y,num_captured] = 1

def make_legality_plane(board, array, stone):
    for x in xrange(board.N):
        for y in xrange(board.N):
            if board.play_is_legal(x, y, stone):
                array[x,y] = 1

def make_feature_planes(board, play_color):
    Nplanes = 3
    feature_planes = np.zeros((board.N, board.N, Nplanes), dtype=np.int8)
    make_stone_plane(feature_planes[:,:,0], board, play_color)
    make_stone_plane(feature_planes[:,:,1], board, flipped_stone(play_color))
    make_stone_plane(feature_planes[:,:,2], board, Stone.Empty)
    #make_ones_plane(feature_planes[:,:,3], board)
    #max_lookback = 8
    #make_history_planes(feature_planes[:,:,4:12], board, max_lookback)
    #max_liberties = 8
    #make_liberty_count_planes(feature_planes[:,:,12:20], board, max_liberties)
    #max_captures = 8
    #make_capture_count_planes(feature_planes[:,:,20:28], board, max_captures, play_color)
    #max_self_atari_size = 8
    #make_self_atari_size_planes(feature_planes[:,:,28:36], board, max_self_atari_size, play_color)
    #max_liberties_after_move = 8
    #make_liberty_count_after_move_planes(feature_planes[:,:,36:44], board, max_liberties_after_move, play_color)
    #make_legality_plane(feature_planes[:,:,44], board, play_color)
    return feature_planes

def make_move_arr(x, y):
    return np.array([x,y], dtype=np.int8)

def show_plane(array):
    assert len(array.shape) == 2
    N = array.shape[0]
    print "=" * N
    for y in xrange(N):
        for x in xrange(N):
            sys.stdout.write('1' if array[x,y]==1 else '0')
        sys.stdout.write('\n')
    print "=" * array.shape[1]

def show_all_planes(array):
    assert len(array.shape) == 3
    for i in xrange(array.shape[2]):
        print "PLANE %d:" % i
        show_plane(array[:,:,i])

def show_feature_planes_and_move(feature_planes, move):
    print "FEATURE PLANES:"
    show_all_planes(feature_planes)
    print "MOVE:"
    print move

def show_batch(all_feature_planes, all_moves):
    batch_size = all_feature_planes.shape[0]
    print "MINIBATCH OF SIZE", batch_size
    for i in xrange(batch_size):
        print "EXAMPLE", i
        show_feature_planes_and_move(all_feature_planes[i,:,:,:], all_moves[i,:])

def test_feature_planes():
    board = Board(5)
    moves = [(0,0), (1,1), (2,2), (3,3), (4,4)]
    play_color = Stone.Black
    for x,y in moves:
        board.show()
        feature_planes = make_feature_planes(board, play_color)
        move_arr = make_move_arr(x, y)
        show_feature_planes_and_move(feature_planes, move_arr)
        print
        board.play_stone(x, y, play_color)
        play_color = flipped_stone(play_color)

def write_minibatch(filename, all_feature_planes, all_moves):
    assert all_feature_planes.dtype == np.int8
    assert all_moves.dtype == np.int8
    assert len(all_feature_planes.shape) == 4
    assert len(all_moves.shape) == 2
    assert all_feature_planes.shape[0] == all_moves.shape[0]
    print "writing %s" % filename
    np.savez_compressed(filename, feature_planes=all_feature_planes, moves=all_moves)

def read_minibatch(filename):
    npz = np.load(filename)
    ret = (npz['feature_planes'], npz['moves'])
    npz.close()
    return ret

def test_minibatch_read_write():
    N = 5
    board = Board(N)
    moves = [(0, 0), (1, 1), (2, 2)]
    minibatch_size = len(moves)
    num_feature_planes = 3
    all_feature_planes = np.zeros((minibatch_size, N, N, num_feature_planes), dtype=np.int8)
    all_moves = np.zeros((minibatch_size, 2), dtype=np.int8)
    play_color = Stone.Black
    for i in xrange(minibatch_size):
        print "out example %d" % i
        x,y = moves[i]
        board.show()
        all_feature_planes[i,:,:,:] = make_feature_planes(board, play_color)
        all_moves[i,:] = make_move_arr(x, y)
        show_feature_planes_and_move(all_feature_planes[i,:,:,:], all_moves[i,:])
        print
        board.play_stone(x, y, play_color)
        play_color = flipped_stone(play_color)

    filename = "/tmp/test_minibatch.npz"
    print "writing minibatch..."
    write_minibatch(filename, all_feature_planes, all_moves)
    print "reading minibatch..."
    write_minibatch(filename, all_feature_planes, all_moves)
    (in_feature_planes, in_moves) = read_minibatch(filename)

    for i in xrange(minibatch_size):
        print "in example %d" % i
        show_feature_planes_and_move(in_feature_planes[i,:,:,:], in_moves[i,:])



class TrainingDataWriter:
    def __init__(self, N, out_dir, minibatch_size, num_features, rank_allowed):
        self.out_dir = out_dir
        self.player = PlayingProcessor(N)
        self.minibatch_features = np.empty((minibatch_size, N, N, num_features), dtype=np.int8)
        self.minibatch_moves = np.empty((minibatch_size, 2), dtype=np.int8)
        self.example_index = 0
        self.minibatch_number = 0
        self.minibatch_size = minibatch_size
        self.num_features = num_features
        self.rank_allowed = rank_allowed
        #self.known_ranks = set()

    def __enter__(self):
        self.fout = open(self.training_data_file, 'w')

    def __exit__(self, exception_type, exception_value, traceback):
        self.fout.close()

    def begin_game(self):
        self.player.begin_game()
        self.ignore_game = False
    
    def end_game(self):
        self.player.end_game()

    def write_move(self, play_color, move_str):
        vertex = parse_vertex(move_str)
        if not vertex: return # play passed
        x,y = vertex
        self.minibatch_features[self.example_index,:,:,:] = make_feature_planes(self.player.board, play_color)
        self.minibatch_moves[self.example_index,:] = make_move_arr(x, y)
        self.example_index += 1
        if self.example_index == self.minibatch_size:
            filename = "%s/train_mb%d_fe%d.%d" % (self.out_dir, self.minibatch_size, 
                                                  self.num_features, self.minibatch_number)
            write_minibatch(filename, self.minibatch_features, self.minibatch_moves)
            self.example_index = 0
            self.minibatch_number += 1


    def process(self, property_name, property_data):
        if self.ignore_game: return

        if property_name == "W":
            self.write_move(Stone.White, property_data)
        elif property_name == "B":
            self.write_move(Stone.Black, property_data)
        elif property_name == "WR" or property_name == "BR":
            #if not property_data in self.known_ranks:
                #self.known_ranks.add(property_data)
                #print "new rank %s, now ranks =" % property_data, self.known_ranks
            if not self.rank_allowed(property_data): 
                self.ignore_game = True
                print "ignoring game because it has non-allowed rank:", property_data

        self.player.process(property_name, property_data)

def test_TrainingDataWrite():
    N = 19
    sgf = "/home/greg/coding/ML/go/NN/data/KGS/SGFs/kgs-19-2009-09-new/2009-09-14-52.sgf"
    print "going to read the game at", sgf

    print "let's play through the game first:"
    parse_SGF(sgf, PrintingProcessor(N))

    print "OK, now let's process it into minibatches:"
    out_dir = "/tmp/train_data_test"
    minibatch_size = 10
    num_features = 3
    writer = TrainingDataWriter(N, out_dir, minibatch_size, num_features)
    parse_SGF(sgf, writer)

    print "Now we will try to read the written minibatch files:"
    for mbfile in os.listdir(out_dir):
        filename = os.path.join(out_dir, mbfile)
        print "filename =", filename
        mb_features, mb_moves = read_minibatch(filename)
        show_batch(mb_features, mb_moves)

def make_KGS_training_data():
    N = 19
    minibatch_size = 8192
    num_features = 3
    out_dir = "/home/greg/coding/ML/go/NN/data/KGS/processed/mb%d_fe%d" % (minibatch_size, num_features)
    rank_allowed = lambda rank: rank in ['1d', '2d', '3d', '4d', '5d', '6d', '7d', '8d', '9d', '10d',
                                         '1p', '2p', '3p', '4p', '5p', '6p', '7p', '8p', '9p', '10p']
    writer = TrainingDataWriter(N, out_dir, minibatch_size, num_features, rank_allowed)
    base_dir = "/home/greg/coding/ML/go/NN/data/KGS/SGFs"
    num_games = 0
    for period_dir in os.listdir(base_dir):
        for sgf_file in os.listdir(os.path.join(base_dir, period_dir)):
            filename = os.path.join(base_dir, period_dir, sgf_file)
            parse_SGF(filename, writer)
            num_games += 1
            if num_games % 100 == 0: print "num_games =", num_games
            #if num_games == 1000: return

def make_CGOS9x9_training_data():
    N = 9
    minibatch_size = 100000
    num_features = 3
    out_dir = "/home/greg/coding/ML/go/NN/data/CGOS/9x9/processed/mb%d_fe%d" % (minibatch_size, num_features)
    rank_allowed = lambda rank: True
    writer = TrainingDataWriter(N, out_dir, minibatch_size, num_features, rank_allowed)
    base_dir = "/home/greg/coding/ML/go/NN/data/CGOS/9x9/SGFs"
    num_games = 0
    for year_dir in os.listdir(base_dir):
        for month_dir in os.listdir(os.path.join(base_dir, year_dir)):
            for day_dir in os.listdir(os.path.join(base_dir, year_dir, month_dir)):
                for sgf_file in os.listdir(os.path.join(base_dir, year_dir, month_dir, day_dir)):
                    filename = os.path.join(base_dir, year_dir, month_dir, day_dir, sgf_file)
                    parse_SGF(filename, writer)
                    num_games += 1
                    if num_games % 100 == 0: print "num_games =", num_games
        

if __name__ == "__main__":
    #test_feature_planes()
    #test_minibatch_read_write()
    #test_TrainingDataWrite()
    
    #make_KGS_training_data()
    make_CGOS9x9_training_data()
    
    #import cProfile
    #cProfile.run('make_KGS_training_data()')





