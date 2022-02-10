# coding=utf-8

import os

import MySQLdb

import deal

import numpy as np

from itertools import chain

import numpy as np

float_formatter = lambda x: "%.2f" % x
np.set_printoptions(formatter={'float_kind': float_formatter})


def TimeSeriesSimilarityImprove(s1, s2):
    # 取较大的标准差
    sdt = np.std(s1, ddof=1) if np.std(s1, ddof=1) > np.std(s2, ddof=1) else np.std(s2, ddof=1)
    print("两个序列最大标准差:" + str(sdt))
    l1 = len(s1)
    l2 = len(s2)
    paths = np.full((l1 + 1, l2 + 1), np.inf)  # 全部赋予无穷大
    sub_matrix = np.full((l1, l2), 0)  # 全部赋予0
    max_sub_len = 0
    print(l1)
    print(l2)
    paths[0, 0] = 0
    for i in range(l1):
        for j in range(l2):
            d = s1[i] - s2[j]
            cost = d ** 2
            paths[i + 1, j + 1] = cost + min(paths[i, j + 1], paths[i + 1, j], paths[i, j])
            if np.abs(s1[i] - s2[j]) < sdt:
                if i == 0 or j == 0:
                    sub_matrix[i][j] = 1
                else:
                    sub_matrix[i][j] = sub_matrix[i - 1][j - 1] + 1
                    max_sub_len = sub_matrix[i][j] if sub_matrix[i][j] > max_sub_len else max_sub_len

    paths = np.sqrt(paths)
    s = paths[l1, l2]
    print(s)
    return s, paths.T, [max_sub_len],sdt


def calculate_attenuate_weight(seqLen1, seqLen2, com_ls):
    weight = 0
    for comlen in com_ls:
        weight = weight + comlen / seqLen1 * comlen / seqLen2
    return 1 - weight


class memory():
    def __init__(self, host, port, user, passwd, db):
        '''
        初始化的方法，主要是存储连接数据库的参数
        :param host:
        :param port:
        :param user:
        :param passwd:
        :param db:
        '''
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.db = db

    def addsong(self, path):
        '''
        添加歌曲方法，将歌曲名和歌曲特征指纹存到数据库
        :param path: 歌曲路径
        :return:
        '''
        if type(path) != str:
            raise(TypeError, 'path need string')
        basename = os.path.basename(path)
        try:
            conn = MySQLdb.connect(host=self.host, port=self.port, user=self.user, passwd=self.passwd, db=self.db,
                                   charset='utf8')
        except:
            print('DataBase error')
            return None
        cur = conn.cursor()
        namecount = cur.execute("select * from record_search.musicdata WHERE song_name = '%s'" % basename)
        if namecount > 0:
            print('the song has been record!')
            return None
        v = deal.voice()
        v.loaddata(path)
        v.fft()
        cur.execute("insert into record_search.musicdata VALUES('%s','%s')" % (basename, v.high_point.__str__()))
        conn.commit()
        cur.close()
        conn.close()


    def fp_compare(self, search_fp, match_fp):
        '''

        :param search_fp: 查询指纹
        :param match_fp: 库中指纹
        :return:最大相似值 float
        '''
        if len(search_fp) > len(match_fp):
            return 0
        max_similar = 0
        search_fp_len = len(search_fp)
        match_fp_len = len(match_fp)
        for i in range(match_fp_len - search_fp_len):
            temp = 0
            for j in range(search_fp_len):
                if match_fp[i + j] == search_fp[j]:
                    temp += 1
            if temp > max_similar:
                max_similar = temp
        return max_similar


    def fp_compare_sdt(self, search_fp, match_fp):
        '''

        :param search_fp: 查询指纹
        :param match_fp: 库中指纹
        :return:最大相似值 float
        '''
        if len(search_fp) > len(match_fp):
            return 0
        max_similar = 0
        search_fp_len = len(search_fp)
        match_fp_len = len(match_fp)
        
        search_fp_b = list(chain.from_iterable(search_fp))
        match_fp_b = list(chain.from_iterable(match_fp))
        sdt = np.std(search_fp, ddof=1) if np.std(search_fp, ddof=1) > np.std(match_fp, ddof=1) else np.std(match_fp, ddof=1)

        return sdt



    def fp_compare_dtw(self, search_fp, match_fp):
        '''

        :param search_fp: 查询指纹
        :param match_fp: 库中指纹
        :return:最大相似值 float
        '''
        if len(search_fp) > len(match_fp):
            return 0
        max_similar = 0
        search_fp_len = len(search_fp)
        match_fp_len = len(match_fp)
        
        search_fp_b = list(chain.from_iterable(search_fp))
        match_fp_b = list(chain.from_iterable(match_fp))
        temp, paths12, max_sub12=TimeSeriesSimilarityImprove(search_fp_b,match_fp_b)
        weight12 = calculate_attenuate_weight(len(search_fp_b), len(match_fp_b), max_sub12)

        print(temp*weight12)
        return temp*weight12

    def search(self, path):
        '''
        搜索方法，输入为文件路径
        :param path: 待检索文件路径
        :return: 按照相似度排序后的列表，元素类型为tuple，二元组，歌曲名和相似匹配值
        ''' 
        #先计算出来我们的音频指纹
        v = deal.voice()
        v.loaddata(path)
        v.fft()
        #尝试连接数据库
        try:
            conn = MySQLdb.connect(host=self.host, port=self.port, user=self.user, passwd=self.passwd, db=self.db,
                                   charset='utf8')
        except:
            raise(IOError, 'DataBase error')
        cur = conn.cursor()
        cur.execute("SELECT * FROM record_search.musicdata")
        result = cur.fetchall()
        compare_res = []
        for i in result:
            # compare_res.append((self.fp_compare_sdt(v.high_point[:-1], eval(i[1])), i[0]))
            compare_res.append((self.fp_compare_dtw(v.high_point[:-1], eval(i[1])), i[0]))
            # compare_res.append((self.fp_compare(v.high_point[:-1], eval(i[1])), i[0]))
        compare_res.sort(reverse=False)
        cur.close()
        conn.close()
        print("compare_res")
        print(compare_res)
        return compare_res

    def search_and_play(self, path):
        '''
        搜索方法顺带了播放方法
        :param path:文件路径
        :return:
        '''
        v = deal.voice()
        v.loaddata(path)
        v.fft()
        try:
            conn = MySQLdb.connect(host=self.host, port=self.port, user=self.user, passwd=self.passwd, db=self.db,
                                   charset='utf8')
        except:
            print('DataBase error')
            return None
        cur = conn.cursor()
        cur.execute("SELECT * FROM record_search.musicdata")
        result = cur.fetchall()
        compare_res = []
        for i in result:
            #compare_res.append((self.fp_compare_sdt(v.high_point[:-1], eval(i[1])), i[0]))
            compare_res.append((self.fp_compare_dtw(v.high_point[:-1], eval(i[1])), i[0]))
            # compare_res.append((self.fp_compare(v.high_point[:-1], eval(i[1])), i[0]))
        compare_res.sort(reverse=False)
        cur.close()
        conn.close()
        print("compare_res2")
        print(compare_res)
        v.play(compare_res[0][1])
        return compare_res


if __name__ == '__main__':
    sss = memory('localhost', 3306, 'root', 'root', 'record_search')
    sss.addsong('dw.wav')
    sss.addsong('kr.wav')
    sss.addsong('Bicycle.wav')
    sss.addsong('rose_someonelikeyou.wav')
    sss.addsong('xt.wav')

    sss.search('record_pianai.wav')

    # sss.search_and_play('record_pianai.wav')
