import argparse
from usgs.download.multithreaded_downloader import MultiThreadedDownloader


if __name__ == '__main__':
    # User input
    parser = argparse.ArgumentParser()

    parser.add_argument('-u', '--username', default=os.getenv("USGS_USERNAME"), help='Username')
    parser.add_argument('-p', '--password', default=os.getenv("USGS_PASSWORD"), help='Password')
    parser.add_argument('-f', '--filename', required=True, help='download entityId list')
    parser.add_argument('-o', '--output-folder', default=".", help='output folder path')
    parser.add_argument('-s', '--file-suffixes', nargs="+", help='specify file suffix to download')
    parser.add_argument('-e', '--entity-id-path', type=str, help='read/write an entity id cache at this path',
                        default=None)
    parser.add_argument('-l', '--limit', type=int, help='limit to this many items', default=None)

    args = parser.parse_args()

    dl = MultiThreadedDownloader()
    dl.fetch(args.username, args.password, args.scenefile, args.output_folder, args.entity_id_path, args.limit,
             args.suffixes)