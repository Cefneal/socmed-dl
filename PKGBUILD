# Maintainer: Cefneal
# PKGBUILD for socmed-dl - Social Media Downloader

pkgname=socmed-dl
pkgver=2.2.1
pkgrel=1
pkgdesc="Download video/music from 10+ platforms, convert to x265/AV1/VP9"
arch=('any')
url="https://github.com/Cefneal/socmed-dl"
license=('MIT')
depends=(
    'python'
    'python-rich'
    'yt-dlp'
    'ffmpeg'
)
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
source=("$pkgname-$pkgver.tar.gz::https://github.com/Cefneal/socmed-dl/archive/v$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
    cd "$srcdir/$pkgname-$pkgver"
    python -m build --wheel --no-isolation
}

package() {
    cd "$srcdir/$pkgname-$pkgver"
    python -m installer --destdir="$pkgdir" dist/*.whl
    install -Dm644 pyproject.toml "$pkgdir/usr/share/doc/$pkgname/pyproject.toml"
}
