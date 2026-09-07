from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import KnowledgeArticle
from .services import embeddings


@receiver(post_save, sender=KnowledgeArticle)
def update_knowledge_article_embedding(sender, instance, raw, **kwargs):
    if raw:
        return

    embedding = embeddings.embed_text(f"{instance.title}\n\n{instance.content}")

    
    KnowledgeArticle.objects.filter(pk=instance.pk).update(embedding=embedding)
