from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class Board(models.Model):
    """
    여러 게시판을 구분하기 위한 모델.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Post(models.Model):
    """
    각 게시판(Board)에서 작성되는 글
    - board: 어느 게시판에 속하는 글인지
    - link_url: 첨부 링크
    - hidden_by: 글을 숨긴 유저들 (내 피드에서 이 글을 안 보이게 하려면 필터링)
    - 추천/비추천 : Like 테이블에서 관리 (PostLike)
    - 스크랩 : M2M (scrapped_by) 로 관리
    """
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    author_nickname = models.CharField(max_length=50, blank=True)
    content = models.TextField()
    images = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    scrapped_by = models.ManyToManyField(User, related_name='scrapped_posts', blank=True)
    hidden_by = models.ManyToManyField(User, related_name='hidden_posts', blank=True)

    def __str__(self):
        return f"Post({self.id}) by {self.author.username}: {self.content[:20]}"
    
    def save(self, *args, **kwargs):
        if not self.author_nickname:  # 새 게시글 작성 시, 닉네임 자동 설정
            self.author_nickname = self.author.profile.nickname
        super().save(*args, **kwargs)

    @property
    def like_count(self):
        return self.likes.count()


class LikeType(models.TextChoices):
    LIKE = 'LIKE', '추천'
    DISLIKE = 'DISLIKE', '비추천'

class PostLike(models.Model):
    """
    게시물 좋아요
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')

    def __str__(self):
        return f"{self.user.username} LIKE post {self.post.id}"

class Comment(models.Model):
    """
    댓글/대댓글 구조
    - parent = None이면 일반 댓글
    - parent != None이면 특정 댓글의 대댓글(답글)
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    author_nickname = models.CharField(max_length=50, blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    hidden_by = models.ManyToManyField(User, related_name="hidden_comments", blank=True) 


    def __str__(self):
        return f"Comment by {self.author.username}"

    def save(self, *args, **kwargs):
        if not self.author_nickname:  # 새 댓글 작성 시, 닉네임 자동 설정
            self.author_nickname = self.author.profile.nickname
        super().save(*args, **kwargs)

    @property
    def is_reply(self):
        return self.parent is not None

class CommentLike(models.Model):
    """
    댓글 좋아요 (comment에 대한 'UP'개념)
    """
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('comment', 'user')

    def __str__(self):
        return f"{self.user.username} LIKE comment {self.comment.id}"

    
class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_histories')
    keyword = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'keyword')  # 중복 방지

