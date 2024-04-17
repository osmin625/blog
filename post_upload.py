from os import path, listdir, makedirs, rename, remove, getenv
import zipfile
import shutil
import fileinput
import re
import logging
from argparse import ArgumentParser


parser = ArgumentParser()
parser.add_argument('-a', help=' : Running whole functions include fileDistribute when executing the script.', default=False)
parser.add_argument('-d', help=' : Running the distribute function only.', default=False)
args = parser.parse_args()

logging.basicConfig(filename="post_upload.log", encoding='utf-8', level=logging.INFO)

userName = getenv('username')
downloadPath = path.join('\\Users',userName,'Downloads')
contentPath = '\\Users\\Ohseungmin\\workspace\\blog\\frontend\\content\\posts'
# print(path.isdir(contentPath))
imgPath = '\\Users\\Ohseungmin\\workspace\\blog\\frontend\\static\\imgs'
currentPath = path.curdir
sourcePath = path.join(currentPath, 'draft_files')


def getZipList(downloadPath):
    dwPathFiles = listdir(downloadPath)
    zips_ = []

    for f in dwPathFiles:
        filePath = path.join(downloadPath,f)
        fname, ext = path.splitext(f)
        if ext == '.zip' and 'Export' in fname:
            zips_.append(filePath)
    return zips_


def extractZip(path_ = downloadPath):
    if not path.isdir(sourcePath): 
        makedirs(sourcePath)
    for zf in getZipList(path_):
        with zipfile.ZipFile(zf, 'r') as zipRef:
            zipRef.extractall(sourcePath)


def move_md_(fname, path_, src_path = sourcePath):
    src = path.join(src_path, fname)
    dest = path.join(path_, fname)
    rename(src, dest)


def fileDistribute(path_):
    fname_md, fname_dir = set(), set()
    def _fileDistribute(path_):
        for file in listdir(path_):
            fname, ext = path.splitext(file)
            if ext == '.md':
                fname_md.add(fname)
                move_md_(file, contentPath)
            elif ext == '.png':
                move_md_(file, imgPath, path_)
            elif ext == '':
                fname_dir.add(fname)
            else:
                remove(path.join(path_, file))
    _fileDistribute(path_)
    

    mdImgDir = fname_dir & fname_md

    for fname_md in mdImgDir:
        _fileDistribute(path.join(path_, fname_md))

    shutil.rmtree(sourcePath)


def organizeNotionExportFile(path_):
    for file in listdir(path_):
        fname, ext = path.splitext(file)
        if ext not in ['.md', '']:
            remove(path.join(path_, file))
            continue
        if not ext and fname + '.md' not in listdir(path_):
            shutil.rmtree(path.join(path_, fname))
            continue
        fname = ' '.join(fname.split()[:-1])
        new_file = fname + ext
        rename(path.join(path_,file), path.join(path_, new_file))
    return listdir(path_)


def updateImageFileName(path_):
    def _updateImageFileName(path_, folder_name):
        path_ = path.join(path_, folder_name)
        for img in listdir(path_):
            fname, ext = path.splitext(img)
            fnameToken = fname.split()
            idx = fnameToken[-1] if len(fnameToken) > 1 else '0'
            rename(path.join(path_, img), path.join(path_, folder_name + idx + ext))
        logging.info(f'[Image Name Changed] {img} -> {folder_name + idx + ext}')
    
    for file in listdir(path_):
        if path.isdir(path.join(path_, file)):
            _updateImageFileName(path_, file)


def cleanFileNames(path_):
    pattern = re.compile(r'[^\w\d_]+')
    renameCount = 0
    for file in listdir(path_):
        fname, ext = path.splitext(file)
        fname = re.sub(pattern, '_', fname)
        fname = fname.lower()
        if fname.endswith('_'):
            fname = fname.rstrip('_')
        rename(path.join(path_, file), path.join(path_, fname + ext))
        renameCount += 1
    logging.info(f'[{renameCount} files name successfully changed]')
    return renameCount

def updatePostContent(path_):
    mdList = [mdFile for mdFile in listdir(path_) if mdFile.endswith('.md')]

    for file in mdList:
        fname, _ = path.splitext(file)
        
        if path.isdir(path.join(path_,fname)):
            imgList = [imgFile for imgFile in listdir(path.join(path_,fname))]
            # print(imgList)
            imgIdx = 0
        
        FrontMatterClosed = False
        with fileinput.FileInput(path.join(path_,file),inplace=True, encoding='utf-8') as f:
            insideOfLatexBlock = False
            paramCheck = {'categories':False, 'tags':False}
            for line in f:
                # frontmatter 생성
                if f.isfirstline():
                    title = line.lstrip('#')
                    titleParam = 'title:' + title
                    print('---')
                    line = titleParam
                if not FrontMatterClosed:
                    if line == '\n':
                        continue
                    elif f.lineno() > 2 and ':' not in line:
                        FrontMatterClosed = True
                        print('type: post')
                        print('---')
                        for p in paramCheck:
                            if not paramCheck[p]:
                                logging.warning(f'[{file}] The [{p}] parameter does not exist in the frontmatter of the post.')
                    
                    # 노션 DB에 존재하는 column들
                    elif line.startswith(('마지막 학습일:', 'status:', '갱신:', 
                                          'summary:', '생성일:', '생성일0:', 
                                          '하위 항목:', '상위 항목:', '이웃 항목:')):
                        continue

                    # 나는 편의를 위해 노션 DB에 categories, tags column을 만들어두었다.
                    elif line.startswith(('categories:', 'tags:')):
                        param, values = line.split(':')
                        values = values.lstrip().rstrip('\n')
                        paramCheck[param] = True
                        line = f'{param}: [{values}]\n'
                
                # 수식 오류 발생 시 로깅하기
                if '⁍' in line:
                    logging.error(f'[{file}] {f.lineno()-2}th line latex syntax error occured.')
                
                # image path 재설정하기
                elif '![Untitled](' in line:
                    indent_ = line.split('![Untitled]')[0]
                    line = f'{indent_}![{fname}](/imgs/{imgList[imgIdx]})\n'
                    imgIdx += 1
                
                # hugo에서 latex 인식 가능하도록 latex 구문 변경하기
                # 들여쓰기때문에 line 길이로 인식하면 안됨.
                elif '$$' in line and len(line.lstrip()) <= 3: # 블럭 수식
                    indent_ = line.split('$$')[0]
                    if not insideOfLatexBlock:
                        line = indent_ + '`$$\n'
                        insideOfLatexBlock = True
                    else:
                        line = indent_ + '$$`\n'
                        insideOfLatexBlock = False
                
                # 수식이 끝나자마자 시작하는 경우 때문에 $$가 없다를 예외 조건으로 추가하면 안됨.
                elif '$' in line and '`$' not in line and '$`' not in line: # 인라인 수식
                    tokens = line.split('$')
                    insideOfLatexInline = False
                    while len(tokens) > 1: # token들이 하나의 문장으로 합쳐질 때까지 반복.
                        right_, left_ = tokens.pop(), tokens.pop()
                        if not insideOfLatexInline:
                            tokens.append(f'{left_}$`{right_}')
                            insideOfLatexInline = True
                        else:
                            tokens.append(f'{left_}`${right_}')
                            insideOfLatexInline = False
                    line = tokens.pop()
                print(line, end='')

if __name__ == '__main__':
    if args.a or not args.d:
        extractZip(downloadPath)
        organizeNotionExportFile(sourcePath)
        cleanFileNames(sourcePath)
        updateImageFileName(sourcePath)
        updatePostContent(sourcePath)
    if args.a or args.d:
        fileDistribute(sourcePath)
