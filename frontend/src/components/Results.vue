<template>
    <Layout>
        <Header class="header">
            <div class="vcenter">
                <router-link to="/" style="margin-right: 20px; height: 48px">
                    <img src="../assets/ipfs.svg" alt="IPFS" height="100%">
                </router-link>
                <Input
                    title="Search IPFS"
                    :autofocus="true"
                    icon="android-search"
                    placeholder="Search IPFS..."
                    @on-enter="search"
                    @on-click="search"
                    v-model="query"
                    size="large"
                    style="width: 598px"
                    >
                </Input>
            </div>
        </Header>
        <Content style="margin: 0 90px">
            <div class="result-item" v-for="i in 10" :key="i">
                <a slot="title" href="#">
                    <div class="link">
                        <p class="title">星际文件系统- 维基百科，自由的百科全书</p>
                        <p class="url">https://zh.wikipedia.org › zh-hans › 星际...</p>
                    </div>
                </a>
                <p>星际文件系统（InterPlanetary File System，缩写IPFS）是一个旨在创建持久且分布式存储和共享文件的网络传输协议。它是一种内容可寻址（ ...</p>
            </div>
        </Content>
    </Layout>
</template>

<style scoped>
.header {
    padding: 0 20px;
    background-color: white;
    border-bottom: 1px solid #ddd;
    box-shadow: 0 2px 10px #ddd;
}

.vcenter {
    height: 100%;
    display: flex;
    align-items: center;
}

.result-item {
    width: 75vw;
    margin: 26px 0;
}

.title {
    font-size: 18px;
    line-height: 1.2;
    color: #1967D2;
}

.url {
    font-size: 14px;
    color: #006621;
}
</style>

<script>
export default {
  name: 'Results',
  props: ['query'],
  methods: {
    search () {
      this.$router.push(`/search/${this.query}`)
    }
  }
}
</script>
