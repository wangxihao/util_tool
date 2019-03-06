import vtk
import os
import pickle
import json
import scipy.io as io
import numpy as np
import numpy.linalg as LA
from align_trajectory import align_sim3


def save_pickle_file(filename, file):
    with open(filename, 'wb') as f:
        pickle.dump(file, f)
        print("save {}".format(filename))


def load_pickle_file(filename):
    if os.path.exists(filename):
        with open(filename, "rb") as f:
            file = pickle.load(f)
        return file
    else:
        print("{} not exist".format(filename))


def GetTriangleMapper(vertexs, faces):
    points = vtk.vtkPoints()
    for v in vertexs:
        points.InsertNextPoint(v)
    lines = vtk.vtkCellArray()
    line = vtk.vtkLine()
    for f in faces:
        if len(f) == 4:
            line.GetPointIds().SetId(0, f[0] - 1)
            line.GetPointIds().SetId(1, f[1] - 1)
            lines.InsertNextCell(line)
            line.GetPointIds().SetId(0, f[1] - 1)
            line.GetPointIds().SetId(1, f[2] - 1)
            lines.InsertNextCell(line)
            line.GetPointIds().SetId(0, f[2] - 1)
            line.GetPointIds().SetId(1, f[3] - 1)
            lines.InsertNextCell(line)
            line.GetPointIds().SetId(0, f[3] - 1)
            line.GetPointIds().SetId(1, f[1] - 1)
            lines.InsertNextCell(line)
        else:
            if len(f) == 3:
                line.GetPointIds().SetId(0, f[0] - 1)
                line.GetPointIds().SetId(1, f[1] - 1)
                lines.InsertNextCell(line)
                line.GetPointIds().SetId(0, f[1] - 1)
                line.GetPointIds().SetId(1, f[2] - 1)
                lines.InsertNextCell(line)
                line.GetPointIds().SetId(0, f[2] - 1)
                line.GetPointIds().SetId(1, f[0] - 1)
                lines.InsertNextCell(line)

    linesPolyData = vtk.vtkPolyData()
    linesPolyData.SetPoints(points)
    linesPolyData.SetLines(lines)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(linesPolyData)
    return mapper

def GetFaceMapper(vertexs, faces):
    """
    :param vertexs: obj 顶点
    :param faces: 点序
    :return: 传给actor使用的mapper
    """
    # Setup four points
    points = vtk.vtkPoints()
    for v in vertexs:
        points.InsertNextPoint(v[0], v[1], v[2])  # 设置顶点

    # Create the polygon
    polygon = vtk.vtkPolygon()
    polygon.GetPointIds().SetNumberOfIds(4)
    polygons = vtk.vtkCellArray()  # 设置单元 设置拓扑结构
    for i, f in enumerate(faces):
        if len(f) == 4:
            polygon.GetPointIds().SetId(0, f[0] - 1)
            polygon.GetPointIds().SetId(1, f[1] - 1)
            polygon.GetPointIds().SetId(2, f[2] - 1)
            polygon.GetPointIds().SetId(3, f[3] - 1)
        if len(f) == 3:
            polygon.GetPointIds().SetId(0, f[0] - 1)
            polygon.GetPointIds().SetId(1, f[1] - 1)
            polygon.GetPointIds().SetId(2, f[2] - 1)
        polygons.InsertNextCell(polygon)

    polygonPolyData = vtk.vtkPolyData()
    polygonPolyData.SetPoints(points)
    polygonPolyData.SetPolys(polygons)

    mapper = vtk.vtkPolyDataMapper()
    if vtk.VTK_MAJOR_VERSION <= 5:
        mapper.SetInput(polygonPolyData)
    else:
        mapper.SetInputData(polygonPolyData)
    return mapper

def loadObj(path):
    """Load obj file
    读取三角形和四边形的mesh
    返回vertex和face的list
    """
    if path.endswith('.obj'):
        f = open(path, 'r')
        lines = f.readlines()
        vertics = []
        faces = []
        for line in lines:
            if line.startswith('v') and not line.startswith('vt') and not line.startswith('vn'):
                line_split = line.split()
                ver = line_split[1:4]
                ver = [float(v) for v in ver]
                # print(ver)
                vertics.append(ver)
            else:
                if line.startswith('f'):
                    line_split = line.split()
                    if '/' in line:  # 根据需要这里补充obj的其他格式解析
                        tmp_faces = line_split[1:]
                        f = []
                        for tmp_face in tmp_faces:
                            f.append(int(tmp_face.split('/')[0]))
                        faces.append(f)
                    else:
                        face = line_split[1:]
                        face = [int(fa) for fa in face]
                        faces.append(face)
        return vertics, faces

    else:
        print('格式不正确，请检查obj格式')
        return


def writeObj(file_name_path, vertexs, faces):
    """write the obj file to the specific path
       file_name_path:保存的文件路径
       vertexs:顶点数组 list
       faces: 面 list
    """
    with open(file_name_path, 'w') as f:
        for v in vertexs:
            # print(v)
            f.write("v {} {} {}\n".format(v[0], v[1], v[2]))
        for face in faces:
            if len(face) == 4:
                f.write("f {} {} {} {}\n".format(face[0], face[1], face[2], face[3])) # 保存四个顶点
            if len(face) == 3:
                f.write("f {} {} {}\n".format(face[0], face[1], face[2])) # 保存三个顶点
        print("saved mesh to {}".format(file_name_path))

def Quad2Tri(qv, qf):# 将四边形mesh 转化为 三角形mesh
    """
    :param qv: 四边形面的顶点
    :param qf: 四边形面的点序
    :return: 三角形顶点和面片点序以及还原点
    原理是在点序的后面追加点
    点序的分割按照 1 2 3 4---->(1,2,3)(2,3,4)这种方式分割 顶点不变
    """
    trif = []
    self_trif = []
    for face in qf:
        if len(face) == 4:
            f0 = [face[0], face[1], face[2]]
            trif.append(f0)
            f1 = [face[0], face[2], face[3]]
            trif.append(f1)
        else:
            self_trif.append(face)
    index = len(trif)
    tv = qv
    trif.append(self_trif)
    return tv, trif, index


def Tri2Quad(tv, tf, index):  # 将三角mesh 转化为 四边形mesh
    """
    :param tv: 三角形面的的顶点
    :param tf: 三角形边形面的点序
    :index : 还原点 index之后的点序不需要还原
    :return: 四边形顶点和面片点序
    点序的分割按照(1,2,3)(2,3,4)----> 1 2 3 4这种方式分割 顶点不变
    """
    qf = []
    for i in range(0, index, 2):
        qf_tmp = [tf[i][0], tf[i][1], tf[i][2], tf[i+1][2]]
        qf.append(qf_tmp)
    if len(tf) == index:
        pass
    else:
        qf.append(tf[index:])
    return tv, qf


def batch_convert_quad2tri(file_dir, filenames, target_dir):
    """
    description:批量将四边形的面片转化为三角形面片
    :param file_dir: 文件所在目录
    :param filenames: 批量的文件名字
    :param target_dir: 保存的文件夹
    :return: 还原点文件
    """
    index_list = []
    for file in filenames:
        if file.endswith('.obj'):
            file_path = os.path.join(file_dir, file)
            v, f = loadObj(file_path)
            tv, tf, index = Quad2Tri(v, f)
            writeObj(os.path.join(target_dir, file), tv, tf)
            index_list.append(index)
        else:
            pass
    save_pickle_file(os.path.join(target_dir, "index.pkl"), index_list)
    return index_list


def batch_convert_tri2quad(file_dir, filenames, target_dir, index):
    """
    description:批量将三角形的面片转化为四边形的面片
    :param file_dir: 文件所在目录
    :param filenames: 批量的文件名字
    :param target_dir: 保存的文件夹
    :param index: 还原点文件
    :return: 返回最后一个测试用例
    """
    for i, file in enumerate(filenames):
        if file.endswith('.obj'):
            file_path = os.path.join(file_dir, file)
            v, f = loadObj(file_path)
            if isinstance(index,  int):
                qv, qf = Tri2Quad(v, f, index)
            if isinstance(index, list):
                qv, qf = Tri2Quad(v, f, index[i])
            writeObj(os.path.join(target_dir, file), qv, qf)
        else:
            pass
    return qv, qf


def loadmarkpoint(txt_path):
    with open(txt_path, 'r') as f:
        data = json.load(f)
    mark_points = np.array(data)
    return mark_points


def make_Face_Marker(source_obj_path, source_txt, target_obj_path, target_txt, file_mat_path):
    """
    :param source_obj_path: 源obj文件路径
    :param source_txt: 源obj文件的wrap生成的每个标记点的三维坐标文件
    :param target_obj_path: 目标obj文件路径
    :param target_txt: 目标obj文件的wrap生成的每个标记点的三维坐标文件
    :param file_mat_path: 要把保存的.mat 文件的路径
    :return: 返回FaceMarker mat文件的内容的numpy 文件
    """
    v, f = loadObj(source_obj_path)
    markpoints_1 = loadmarkpoint(source_txt)
    row, col = markpoints_1.shape
    ind1 = []
    for i in range(0, row):
        dis_vector = (v - markpoints_1[i, :])  # distance vector

        distance = dis_vector[:, 0] * dis_vector[:, 0] + dis_vector[:, 1] * dis_vector[:, 1] + \
                   dis_vector[:, 2] * dis_vector[:, 2]
        index = np.argmin(distance)
        ind1.append(index + 1)
    v1, f = loadObj(target_obj_path)
    markpoints_2 = loadmarkpoint(target_txt)
    row, col = markpoints_2.shape
    ind2 = []
    for i in range(0, row):
        dis_vector = (v1 - markpoints_2[i, :])  # distance vector
        distance = dis_vector[:, 0] * dis_vector[:, 0] + dis_vector[:, 1] * dis_vector[:, 1] + \
                   dis_vector[:, 2] * dis_vector[:, 2]
        index = np.argmin(distance)
        ind2.append(index + 1)
    FaceMarker = []
    FaceMarker.append(ind1)
    FaceMarker.append(ind2)
    FaceMarker = np.array(FaceMarker, dtype=np.int32).transpose()
    io.savemat(file_mat_path, {'Marker': FaceMarker})
    return FaceMarker


def get_closetest_point_index_from_pointtxt(source_obj_path, source_txt):
    """
    根据指定的obj文件和指定的点的坐标返回坐标点序
    :param source_obj_path: 原obj文件路径
    :param source_txt: 原obj文件对应的点的坐标
    :return: 返回顶点的索引
    """
    v, f = loadObj(source_obj_path)
    markpoints_1 = loadmarkpoint(source_txt)
    row, col = markpoints_1.shape
    ind1 = []
    for i in range(0, row):
        dis_vector = (v - markpoints_1[i, :])  # distance vector

        distance = dis_vector[:, 0] * dis_vector[:, 0] + dis_vector[:, 1] * dis_vector[:, 1] + \
                   dis_vector[:, 2] * dis_vector[:, 2]
        index = np.argmin(distance)
        ind1.append(index + 1)
    return ind1


def Normalize_Obj(file, target_file, scale=1):
    """
    对模型减去均值并保存到指定文件夹
    :param file: 源文件名字
    :param target_file: 目标文件名字
    :return: 归一化并且缩放过模型
    """
    v, f = loadObj(file)
    v_np = np.array(v) * scale
    v_np = v_np - np.mean(v_np, axis=0)
    print("均值: {}".format(np.mean(v_np, axis=0)))
    v = v_np.tolist()
    writeObj(target_file, v, f)
    print("保存 {}".format(target_file))
    return v, f


def con_filename_to_string(txtPathandName, file_path):
    file_names = os.listdir(file_path)
    with open(txtPathandName, "w") as f:
        f.write('[')
        for file_name in file_names:
            f.write("'{}', ".format(file_name))
        f.write(']')
    print('write {}'.format(txtPathandName))


def ExtractFaceVertexIndex(Face_verts, Head_verts, err=1e-9):
    """
    通过给定面部顶点和头部顶点数据返回面部数据在头部数据中的索引位置
    :param Face_verts: 面部顶点数据 list
    :param Head_verts: 头部顶点数据 list
    :err :精度
    :return: 面部顶点数据在头部数据中的索引
    """
    f_v = np.array(Face_verts)
    h_v = np.array(Head_verts)
    index = []
    for v in f_v:
        assert len(v) == 3, '顶点长度不为3'
        h_tmp = h_v - v
        hv_sum = np.sum(h_tmp**2, axis=1)
        ind = np.where(hv_sum <= err)
        # print(ind)
        assert len(ind) >= 1, '点序为空'
        index.append(ind[0][0])
    assert len(index) == len(f_v), "索引与面部数据长度不一致"
    return index


def ExtracFaceFromHead(Head_v, face_index, face_f):
    """
    根据输入头部顶点信息以及对应的面部索引值，返回只包含脸部的数据
    :param Head_v: 头部数据顶点 list
    :param face_index: 面部数据索引 list
    :param face_f: 面部点序 list
    :return: 脸部数据顶点及对应脸部点序 list
    """
    face_v = []
    Head_v = np.array(Head_v)
    for i, ind in enumerate(face_index):
        face_v.append(Head_v[ind, :].tolist())
    return face_v, face_f



def ConvertFace2Head(Face_v, Head_v, Head_f, index):
    """
    根据面部顶点数据和对应的index索引文件, 生成对应的头部obj文件
    :param Face_v: 面部顶点数据 list n,3
    :param Head_v: 整个头部的顶点数据 list n,3
    :param Head_f: 整个头部的点序 list n,3
    :param index: 脸部数据对应整个头部数据的点的索引 list 1, n
    :return: 替换脸部的整个头部的顶点信息和点序
    """
    Face_v = np.array(Face_v)
    Head_v = np.array(Head_v)
    for i, ind in enumerate(index):
        Head_v[ind, :] = Face_v[i, :]
    return Head_v.tolist(), Head_f


def batch_convert_head_to_face(head_path, face_index, face_f, face_path):
    """
    批量将头部数据转化为面部数据
    :param head_path: 头部文件数据路径
    :param face_path: 面部数据文件路径
    :param face_index: 面部数据索引
    :param face_f: 面部点序
    :return: 最后一个转化的face_v face_f
    """
    files = os.listdir(head_path)
    for file_name in files:
        if file_name.endswith('.obj'):
            file = os.path.join(head_path, file_name)
            head_v, head_f = loadObj(file)
            face_v, face_f = ExtracFaceFromHead(head_v, face_index, face_f)
            writeObj(os.path.join(face_path, file_name), face_v, face_f)
        else:
            pass
    return face_v, face_f


def batch_convert_face_to_head(faces_path, save_head_path, head_v, head_f, face_index):
    """
    批量将面部部数据转化为头部数据 即：换脸 使脸部数据公用相同的颈部和后脑勺
    :param faces_path: 面部数据路径
    :param save_head_path: 要保存的头部数据路径
    :param head_v: 要换的头
    :param head_f: 要换的头的点序
    :param face_index: 需要更换的头部数据（面部点）
    :return: 最后一个头部的顶点和点序
    """
    face_file_names = os.listdir(faces_path)
    for file_name in face_file_names:
        if file_name.endswith('.obj'):
            file = os.path.join(faces_path, file_name)
            face_v, face_f = loadObj(file)
            Head_v, Head_f = ConvertFace2Head(face_v, head_v, head_f, face_index)
            writeObj(os.path.join(save_head_path, file_name), Head_v, Head_f)
        else:
            pass
    return Head_v, Head_f


def AlignTwoFaceWithRandomPoints(FirstFace_verts, SecondFace_verts, numberof_points=7):
    """
    将第二个人脸对齐到第一个人脸, 通过计算旋转矩阵, 平移矩阵等等 注意第二个像第一个人脸对齐 即要对齐的人脸是第二个参数
    :param FirstFace: 第一个人脸顶点数据 n x 3
    :param SecondFace: 第二个人脸顶点数据 第一个人脸和第二个人最好定数一样 n x 3
    :param numberof_points:选用多少点进行刚体变换
    :return: 返回第二个人脸对齐后的数据
    """
    Number_points = len(FirstFace_verts)
    select_index = np.random.randint(low=0, high=Number_points, size=numberof_points)
    Face1 = np.array(FirstFace_verts)
    Face2 = np.array(SecondFace_verts)
    Face1_select = Face1[select_index, :].T
    Face2_selcet = Face2[select_index, :].T
    s, R, t, _ = align_sim3(Face1_select, Face2_selcet)
    # print("align error is {}".format(error))
    model_aligned = s * R.dot(Face2.T) + t
    alignment_error = model_aligned - Face1.T
    t_error = np.sqrt(np.sum(np.multiply(alignment_error, alignment_error), 0))
    print("model aligned error is {}".format(np.mean(t_error)))
    return model_aligned.T.tolist()


def AlignTwoFaceWithFixedPoints(FirstFace_verts, SecondFace_verts, pointsindex):
    """
    将第二个人脸对齐到第一个人脸, 通过计算旋转矩阵, 平移矩阵等等 注意第二个像第一个人脸对齐 即要对齐的人脸是第二个参数
    :param FirstFace: 第一个人脸顶点数据 n x 3
    :param SecondFace: 第二个人脸顶点数据 第一个人脸和第二个人最好定数一样 n x 3
    :param pointsindex: 需要對齊所使用的點序 一維list
    :return: 返回第二个人脸对齐后的数据
    """
    select_index = np.array(pointsindex)
    Face1 = np.array(FirstFace_verts)
    Face2 = np.array(SecondFace_verts)
    Face1_select = Face1[select_index, :].T
    Face2_selcet = Face2[select_index, :].T
    s, R, t, _ = align_sim3(Face1_select, Face2_selcet)
    # print("align error is {}".format(error))
    model_aligned = s * R.dot(Face2.T) + t
    alignment_error = model_aligned - Face1.T
    t_error = np.sqrt(np.sum(np.multiply(alignment_error, alignment_error), 0))
    print("model aligned error is {}".format(np.mean(t_error)))
    return model_aligned.T.tolist()


def BatchAlignFacewithRandomPoints(FaceToalignPath, FaceAligned_verts, SavePath):
    """
    批量稳定人脸
    :param FaceToalignPath: 要对齐的人脸路径
    :param FaceAligned_verts: 选好的对齐人脸顶点
    :param SavePath: 要保存的路径
    :return: 最后一个对齐的人脸
    """
    file_names = os.listdir(FaceToalignPath)
    for filename in file_names:
        if filename.endswith('.obj'):
            file = os.path.join(FaceToalignPath, filename)
            ToAlign_v, ToAlign_f = loadObj(file)
            aligned_v = AlignTwoFaceWithRandomPoints(FaceAligned_verts, ToAlign_v)
            writeObj(os.path.join(SavePath, filename), aligned_v, ToAlign_f)


def BatchAlignFacewithFixedPoints(FaceToalignPath, FaceAligned_verts, SavePath, points_index):
    """
    批量稳定人脸
    :param FaceToalignPath: 要对齐的人脸路径
    :param FaceAligned_verts: 选好的对齐人脸顶点
    :param SavePath: 要保存的路径
    :return: 最后一个对齐的人脸
    """
    file_names = os.listdir(FaceToalignPath)
    for filename in file_names:
        if filename.endswith('.obj'):
            file = os.path.join(FaceToalignPath, filename)
            ToAlign_v, ToAlign_f = loadObj(file)
            aligned_v = AlignTwoFaceWithFixedPoints(FaceAligned_verts, ToAlign_v, points_index)
            writeObj(os.path.join(SavePath, filename), aligned_v, ToAlign_f)


def VTK_show(f_v, f_f, tri=True):
    """
    显示物体
    :param f_v:
    :param f_f:
    :return: 无
    """
    if tri:
        mapper = GetTriangleMapper(f_v, f_f)  # 三角形
    else:
        mapper = GetFaceMapper(f_v, f_f)  # 四边形

    colors = vtk.vtkNamedColors()

    actor = vtk.vtkActor()  # new actor
    actor.SetMapper(mapper)
    actor.GetProperty().SetLineWidth(0.1)
    actor.GetProperty().SetColor(colors.GetColor3d("Peacock"))

    render = vtk.vtkRenderer()  # new renderer
    render.AddActor(actor)
    render.SetBackground(0, 0, 0)  # 设置背景颜色

    renderWindow = vtk.vtkRenderWindow()  # new renderWindow
    renderWindow.AddRenderer(render)
    renderWindow.Render()  # 要先render 才可以显示名字

    renderWindow.SetWindowName("examples")

    irenderWindow = vtk.vtkRenderWindowInteractor()  # new interactive window
    irenderWindow.SetRenderWindow(renderWindow)

    irenderWindow.Initialize()
    irenderWindow.Start()


if __name__ == '__main__':
    '''unit test'''
    """批量四边形转为三角形转换主程序"""
    # file_dir = "C:\\Users\\Administrator\\Desktop\\xiaoyue_OBJ_Seq"
    # filenames = ["xiaoyue.0001.obj", "xiaoyue.0002.obj", "xiaoyue.0003.obj", "xiaoyue.0004.obj", "xiaoyue.0005.obj",
    #             "xiaoyue.0006.obj",
    #             "xiaoyue.0007.obj", "xiaoyue.0008.obj", "xiaoyue.0009.obj", "xiaoyue.0010.obj", "xiaoyue.0011.obj",
    #             "xiaoyue.0012.obj",
    #             "xiaoyue.0013.obj", "xiaoyue.0014.obj"]
    # target_dir = "./triangemesh-source"
    # index_list = batch_convert_quad2tri(file_dir, filenames, target_dir)
    # file_tri = "./triangemesh-source"
    # target_file = "./quad_mesh"
    # qv, qf = batch_convert_tri2quad(file_tri, filenames, target_file, index_list)

    """
    将小月四边形转化为三角形面
    """
    # charactor_dir = "D:\\Blendshape-Based Animation\\Alien"
    # charactor_name = "alien.obj"
    # qv, qf = loadObj(os.path.join(charactor_dir, charactor_name))
    # tv, tf, index = Quad2Tri(qv, qf)
    # writeObj(os.path.join(charactor_dir, "alien_tri.obj"), tv, tf)
    # save_pickle_file(os.path.join(charactor_dir, 'index.pkl'), index)

    """
    批量将迁移过后的pose的三角形mesh 转化为四边形面片
    """
    # file_dir = "D:\\Blendshape-Based Animation\\charactor_triangles"
    # filenames = ["xiaoyue.0001.obj", "xiaoyue.0002.obj", "xiaoyue.0003.obj", "xiaoyue.0004.obj", "xiaoyue.0005.obj",
    #              "xiaoyue.0006.obj",
    #              "xiaoyue.0007.obj", "xiaoyue.0008.obj", "xiaoyue.0009.obj", "xiaoyue.0010.obj", "xiaoyue.0011.obj",
    #              "xiaoyue.0012.obj",
    #              "xiaoyue.0013.obj", "xiaoyue.0014.obj"]
    # target_dir = "D:\\Blendshape-Based Animation\\charactor_quads"
    # index_list = load_pickle_file('D:\\Blendshape-Based Animation\\charactor\\index.pkl')
    # qv, qf = batch_convert_tri2quad(file_dir, filenames, target_dir, index_list)

    """
    制作matlab 使用的face maker 文件
    """
    # source_obj_path = os.path.join('D:\\Blendshape-Based Animation\\triangemesh-source', "xiaoyue.0013.obj")
    # source_txt = os.path.join('D:\\Blendshape-Based Animation\\triangemesh-source', 'neural-source-points.txt')
    # target_obj_path = os.path.join('D:\\Blendshape-Based Animation\\charactor', 'Xiaoyue_tri.obj')
    # target_txt = os.path.join('D:\\Blendshape-Based Animation\\charactor', 'neural-target-points.txt')
    # file_mat_path= os.path.join('D:\\Deformation-Transfer-Matlab-master', 'Face_Marker.mat')
    # facemarker = make_Face_Marker(source_obj_path, source_txt, target_obj_path, target_txt, file_mat_path)

    """
    批量将四边形AU转化为三角面
    """
    # file_dir = "D:\\Blendshape-Based Animation\\AU_quad"
    # filenames = os.listdir(file_dir)
    # target_dir = "D:\\Blendshape-Based Animation\\AUTri"
    # index_list = batch_convert_quad2tri(file_dir, filenames, target_dir)
    # file_tri = "./triangemesh-source"
    # target_file = "./quad_mesh"
    # con_filename_to_string(os.path.join(file_dir, 'filenames.txt'), file_dir)
    # qv, qf = batch_convert_tri2quad(file_tri, filenames, target_file, index_list)

    """
    批量将迁移过后的pose的三角形mesh 转化为四边形面片
    """
    file_dir = "D:\\Blendshape-Based Animation\\charactor\\Chactor_Au_aigned_tri"
    filenames = os.listdir(file_dir)
    target_dir = "D:\\Blendshape-Based Animation\\charactor\\Charactor_Au_aligned_quads"
    index_list = load_pickle_file('D:\\Blendshape-Based Animation\\charactor\\index.pkl')
    qv, qf = batch_convert_tri2quad(file_dir, filenames, target_dir, index_list)

    """
    去均值化
    """
    # file_dir = 'D:\\Blendshape-Based Animation\\Alien'
    # file_name = 'alien_tri.obj'
    # file = os.path.join(file_dir, file_name)
    # obj = Normalize_Obj(file, os.path.join(file_dir, file_name), 20)

    """
    制作matlab 使用的face maker 文件（外星人的）
    """
    # source_obj_path = os.path.join('D:\\Blendshape-Based Animation\\triangemesh-source', "xiaoyue.0013.obj")
    # source_txt = os.path.join('D:\\Blendshape-Based Animation\\triangemesh-source', 'neural-source-points.txt')
    # target_obj_path = os.path.join('D:\\Blendshape-Based Animation\\charactor', 'Xiaoyue_tri.obj')
    # target_txt = os.path.join('D:\\Blendshape-Based Animation\\charactor', 'neural-target-points.txt')
    # file_mat_path = os.path.join('D:\\Blendshape-Based Animation\\charactor', 'Face_Marker.mat')
    # facemarker = make_Face_Marker(source_obj_path, source_txt, target_obj_path, target_txt, file_mat_path)
    # print(facemarker[np.array([52, 53, 54]), 1])


    """
    批量提取面部数据与还原测试
    """
    # face_v, face_f = loadObj(os.path.join('D:\\Blendshape-Based Animation\\Alien\\NP_alien\\face', 'Alien_face.obj'))
    # head_v, head_f = loadObj(os.path.join('D:\\Blendshape-Based Animation\\Alien\\NP_alien\\head', 'alien_head_tri.obj'))
    # index = ExtractFaceVertexIndex(face_v, head_v)  # 确定face_index
    # save_pickle_file(os.path.join('D:\\Blendshape-Based Animation\\Alien\\NP_alien\\head', 'face_index.pkl'), index)
    # # head_path = 'D:\\Blendshape-Based Animation\\triangemesh-source'
    # face_path = 'D:\\Blendshape-Based Animation\\Alien\\aligned_face'
    # # f_v, f_f = batch_convert_head_to_face(head_path, index, face_f, face_path)
    # head_path_tosave = 'D:\\Blendshape-Based Animation\\Alien\\Transerfed_Head_Tri_mesh'
    # h_v, h_f = batch_convert_face_to_head(face_path, head_path_tosave, head_v, head_f, index)


    """测试对齐人脸功能"""
    # face_v, face_f = loadObj(os.path.join('D:\\Blendshape-Based Animation\\Alien\\NP_alien\\face', 'Alien_face.obj'))
    # Toalign_face_v, _ = loadObj(os.path.join(face_path, 'xiaoyue.0003.obj'))
    # alignedFace = AlignTwoFaceWithRandomPoints(face_v, Toalign_face_v)
    # writeObj(os.path.join("D:\\Blendshape-Based Animation\\Alien\\aligned_face",'xiaoyue.0003.obj'), alignedFace, face_f)

    """
    批量对齐人脸保存
    """
    # face_v, face_f = loadObj(os.path.join('D:\\Blendshape-Based Animation\\Alien\\NP_alien\\face', 'Alien_face.obj'))
    # face_path = 'D:\\Origin_Deformaion_transfer\\output'
    # saved_path = "D:\\Blendshape-Based Animation\\Alien\\aligned_face"
    # BatchAlignFacewithRandomPoints(face_path, face_v, saved_path)

    """
    批量固定点对齐人脸保存
    """
    # face_v, face_f = loadObj(os.path.join('D:\\Blendshape-Based Animation\\charactor\\charactor_triangles', 'xiaoyue.0013.obj'))
    # face_path = 'D:\\Blendshape-Based Animation\\charactor\\charactor_triangles'
    # saved_path = "D:\\Blendshape-Based Animation\\charactor\\Chactor_Au_aigned_tri"
    # # fixedPoints_index = [1900, 7969, 5271]  # 对齐外星人用的索引
    # fixedPoints_index = [16438, 2977, 984, 14115, 14916, 5011]  # 小姐姐
    # BatchAlignFacewithFixedPoints(face_path, face_v, saved_path, fixedPoints_index)

    """
    显示
    """
    # VTK_show(face_v, face_f, tri=True)
