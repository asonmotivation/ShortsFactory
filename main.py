from VideoGenerator import VideoGenerator


if __name__ == '__main__':
    generator = VideoGenerator()
    # generator._stitch_videos_(r"C:\Users\nimni\PycharmProjects\YoutubeShortsFactory\content\_Haunted_After_Cleaning_Cursed_Attic_-_True_Horror_Story_")
    generator.generate(1, 'nosleep', max_length=1000)
    # generator.close_session()
