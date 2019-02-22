# -*- coding: utf-8 -*-
# @Author: hai
# @Date: 2019-01-21 15:50:00

import os
import queue
import re
import sys
import threading
import time

import urllib3

import Utils.Util as Util

tlist = []


class DownloadInfo():
    link = None
    fileDir = None
    fileName = None
    description = ''
    useProxy = False


class ProxyInfo():
    proxyURL = ''


class DownloadUtil():
    poolNum = 10
    timeOut = 10
    retries = 3
    headers = {}
    threadNum = 1
    threadDownloadList = []
    # 下载队列
    queueDownload = queue.Queue()
    isDestory = False
    proxyInfo = ProxyInfo()
    defaultDownloadDir = None
    banList = []
    useProxysHostList = []
    poolProxy = None
    pool = None

    class _DownloadThread(threading.Thread):
        def run(self):
            print('thread name = {} args = {}'.format(threading.current_thread().name, self._args))
            outer = self._args[0]
            proxyInfo = outer.proxyInfo
            pattern = r'[\\/:*?"<>|\r\n]+'
            timeout = None
            retries = None
            if isinstance(outer.timeOut, int):
                timeout = urllib3.Timeout(total=outer.timeOut)
            elif isinstance(outer.timeOut, urllib3.Timeout):
                timeout = outer.timeOut
            if isinstance(outer.retries, int):
                retries = urllib3.Retry(total=outer.retries)
            elif isinstance(outer.retries, urllib3.Retry):
                retries = outer.timeOut
            pool = urllib3.PoolManager(num_pools=outer.poolNum, headers=outer.headers, timeout=timeout, retries=retries)
            poolProxy = urllib3.ProxyManager(proxy_url=proxyInfo.proxyURL, num_pools=outer.poolNum, headers=outer.headers, timeout=timeout, retries=retries)
            while True:
                if outer.isDestory:
                    break
                if not outer.queueDownload.empty():
                    item = outer.queueDownload.get()
                    if item.fileName:
                        fileName = re.sub(pattern, '-', item.fileName)
                    else:
                        fileName = re.sub(pattern, '-', str(item.link).split('/')[-1])
                    filePath = None
                    if not item.fileDir:
                        filePath = os.path.join(outer.defaultDownloadDir, fileName)
                    else:
                        filePath = os.path.join(item.fileDir, fileName)
                    # logger.info('正在下载: ' + description)
                    try:
                        response = None
                        if item.useProxy:
                            response = poolProxy.request('GET', item.link)
                        else:
                            response = pool.request('GET', item.link)
                        with open(filePath, 'wb') as f:
                            f.write(response.data)
                    except Exception as e:
                        if os.path.exists(filePath):
                            os.remove(filePath)

    def setPoolNum(self, poolNum):
        self.poolNum = poolNum
        return self

    def setTimeOut(self, timeOut):
        self.timeOut = timeOut
        return self

    def setRetries(self, retries):
        self.retries = retries
        return self

    def setHeaders(self, headers):
        self.headers = headers
        return self

    def setThreadNum(self, threadNum):
        self.threadNum = threadNum
        return self

    def setProxyURL(self, proxyURL):
        self.proxyInfo.proxyURL = proxyURL
        return self

    def addDownloadTask(self, url, fileDir=None, fileName=None, description=None):
        host = Util.get_website_domain(url)
        if host in self.banList:
            return
        item = DownloadInfo()
        item.link = url
        item.fileDir = fileDir
        item.fileName = fileName
        item.description = description
        if host in self.useProxysHostList:
            item.useProxy = True
        self.queueDownload.put(item)

    def beginDownload(self, url, fileDir=None, fileName=None, description=None):
        try:
            host = Util.get_website_domain(url)
            if host in self.banList:
                return
            _useProxy = False
            if host in self.useProxysHostList:
                _useProxy = True
            _fileName = None
            pattern = r'[\\/:*?"<>|\r\n]+'
            if fileName:
                _fileName = re.sub(pattern, '-', fileName)
            else:
                _fileName = re.sub(pattern, '-', str(url).split('/')[-1])
            filePath = None
            if not fileDir:
                filePath = os.path.join(self.defaultDownloadDir, _fileName)
            else:
                filePath = os.path.join(fileDir, _fileName)
            # logger.info('正在下载: ' + description)
            try:
                response = None
                if _useProxy:
                    response = self.poolProxy.request('GET', url)
                else:
                    response = self.pool.request('GET', url)
                with open(filePath, 'wb') as f:
                    f.write(response.data)
            except Exception as e:
                if os.path.exists(filePath):
                    os.remove(filePath)
                raise e
        except Exception as e:
            raise e

    def loadBanList(self, banlist):
        for item in banlist:
            self.addBanHost(item)

    def addBanHost(self, host):
        if isinstance(host, str):
            _host = Util.get_website_domain(host)
            if _host not in self.banList:
                self.banList.append(_host)

    def removeBanHost(self, host):
        if isinstance(host, str):
            _host = Util.get_website_domain(host)
            if _host in self.banList:
                self.banList.remove(_host)

    def clearBanHost(self):
        self.banList = []

    def loadUseProxysHostList(self, useProxysHostList):
        if not self.proxyInfo.proxyURL:
            raise Exception('未设置代理信息!')
        for item in useProxysHostList:
            self.addUseProxysHost(item)

    def addUseProxysHost(self, host):
        if not self.proxyInfo.proxyURL:
            raise Exception('未设置代理信息!')
        if isinstance(host, str):
            _host = Util.get_website_domain(host)
            if _host not in self.useProxysHostList:
                self.useProxysHostList.append(_host)

    def removeUseProxysHost(self, host):
        if isinstance(host, str):
            _host = Util.get_website_domain(host)
            if _host in self.useProxysHostList:
                self.useProxysHostList.remove(_host)

    def clearUseProxysHost(self):
        self.useProxysHostList = []

    def buildQueue(self):
        self.destory()
        self.threadDownloadList.clear()
        self.isDestory = False

        self.defaultDownloadDir = os.path.dirname(sys.argv[0])
        if self.defaultDownloadDir.strip() == '':
            self.defaultDownloadDir = sys.path[0]
        self.defaultDownloadDir += '\\download_files\\'
        if not os.path.exists(self.defaultDownloadDir):
            os.mkdir(self.defaultDownloadDir)
        print('defaultDownloadDir is {}\n'.format(self.defaultDownloadDir))

        for i in range(self.threadNum):
            t = self._DownloadThread(name='download-thread-' + str(i), args=(self,))
            t.start()
            t._stop()
            self.threadDownloadList.append(t)
        return self

    def build(self):
        self.defaultDownloadDir = os.path.dirname(sys.argv[0])
        if self.defaultDownloadDir.strip() == '':
            self.defaultDownloadDir = sys.path[0]
        self.defaultDownloadDir += '\\download_files\\'
        if not os.path.exists(self.defaultDownloadDir):
            os.mkdir(self.defaultDownloadDir)
        print('defaultDownloadDir is {}\n'.format(self.defaultDownloadDir))

        timeout = None
        retries = None
        if isinstance(self.timeOut, int):
            timeout = urllib3.Timeout(total=self.timeOut)
        elif isinstance(self.timeOut, urllib3.Timeout):
            timeout = self.timeOut
        if isinstance(self.retries, int):
            retries = urllib3.Retry(total=self.retries)
        elif isinstance(self.retries, urllib3.Retry):
            retries = self.timeOut
        self.pool = urllib3.PoolManager(num_pools=self.poolNum, headers=self.headers, timeout=timeout, retries=retries)
        self.poolProxy = urllib3.ProxyManager(proxy_url=self.proxyInfo.proxyURL, num_pools=self.poolNum, headers=self.headers, timeout=timeout, retries=retries)
        return self

    def destory(self):
        self.isDestory = True
        isOver = True
        while True:
            for t in self.threadDownloadList:
                if t.is_alive():
                    isOver = False
                    break
            if isOver:
                break
            time.sleep(2)
