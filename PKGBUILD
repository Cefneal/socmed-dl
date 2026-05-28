# Maintainer: socmed-dl
# PKGBUILD for socmed-dl - Social Media Downloader

pkgname=socmed-dl
pkgver=1.0.0
pkgrel=1
pkgdesc="Download video/music from YouTube, Facebook, Instagram in x265 format"
arch=('any')
url="https://github.com/socmed-dl/socmed-dl"
license=('MIT')
depends=(
    'python'
    'python-rich'
    'yt-dlp'
    'ffmpeg'
)
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
source=("$pkgname-$pkgver.tar.gz::https://github.com/socmed-dl/socmed-dl/archive/v$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
    cd "$srcdir/$pkgname-$pkgver"
    python -m build --wheel --no-isolation
}

package() {
    cd "$srcdir/$pkgname-$pkgver"
    python -m installer --destdir="$pkgdir" dist/*.whl
}
